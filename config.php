<?php
// filepath: /workspaces/BQSL/config.php
declare(strict_types=1);

session_start();

$db = new PDO(
    'sqlite:' . __DIR__ . '/members.db',
    null,
    null,
    [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]
);

$db->exec(
    'CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        public_key TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )'
);

function require_captcha(): void
{
    if (empty($_SESSION['captcha_verified'])) {
        header('Location: /verify.php');
        exit;
    }
}

function encrypt_gpg_message(string $publicKey, string $message): string
{
    if (
        !str_contains($publicKey, 'BEGIN PGP PUBLIC KEY BLOCK') ||
        str_contains($publicKey, 'BEGIN PGP PRIVATE KEY BLOCK')
    ) {
        throw new RuntimeException('Invalid public key.');
    }

    $home = sys_get_temp_dir() . '/bqsl-gpg-' . bin2hex(random_bytes(16));
    mkdir($home, 0700, true);

    try {
        $keyFile = $home . '/public.asc';
        file_put_contents($keyFile, $publicKey);

        $run = static function (array $args, string $input = '') use ($home): string {
            $command = 'gpg --batch --no-options --homedir '
                . escapeshellarg($home) . ' '
                . implode(' ', array_map('escapeshellarg', $args));

            $process = proc_open(
                $command,
                [
                    0 => ['pipe', 'r'],
                    1 => ['pipe', 'w'],
                    2 => ['pipe', 'w'],
                ],
                $pipes
            );

            if (!is_resource($process)) {
                throw new RuntimeException('Unable to start GPG.');
            }

            fwrite($pipes[0], $input);
            fclose($pipes[0]);

            $stdout = stream_get_contents($pipes[1]);
            $stderr = stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);

            if (proc_close($process) !== 0) {
                throw new RuntimeException('GPG error: ' . $stderr);
            }

            return $stdout;
        };

        $run(['--import', $keyFile]);

        $keys = $run(['--with-colons', '--list-keys']);
        $fingerprint = null;

        foreach (explode("\n", $keys) as $line) {
            $fields = explode(':', $line);
            if (($fields[0] ?? '') === 'fpr' && !empty($fields[9])) {
                $fingerprint = $fields[9];
                break;
            }
        }

        if ($fingerprint === null) {
            throw new RuntimeException('No public-key fingerprint found.');
        }

        return $run(
            ['--trust-model', 'always', '--armor', '--encrypt', '--recipient', $fingerprint],
            $message
        );
    } finally {
        foreach (glob($home . '/*') ?: [] as $file) {
            unlink($file);
        }
        rmdir($home);
    }
}