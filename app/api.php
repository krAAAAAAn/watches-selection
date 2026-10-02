<?php
/*
 * Watch Selection — API minimale (un seul fichier, aucune dépendance).
 *
 *   GET  api.php?a=load      → données (data/watches.json, créé depuis seed/ au premier lancement)
 *   POST api.php?a=save      → enregistre toutes les données (sauvegarde datée de l'ancienne version)
 *   POST api.php?a=fetch     → {id, name, urls[]} : rapatrie une photo distante dans img/<id>/
 *   POST api.php?a=upload    → {id, name, dataUrl} : enregistre une photo envoyée (dépôt, détourage)
 *
 * Pas d'authentification ici : l'accès est protégé en amont (Pangolin).
 */

const DATA_DIR   = __DIR__ . '/data';
const DATA_FILE  = DATA_DIR . '/watches.json';
const BACKUP_DIR = DATA_DIR . '/backup';
const SEED_FILE  = __DIR__ . '/seed/watches.json';
const IMG_DIR    = __DIR__ . '/img';
const KEEP_BACKUPS = 50;
const MAX_IMAGE_BYTES = 15 * 1024 * 1024;

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function reply($data, int $code = 200): void {
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}
function fail(string $msg, int $code = 400): void { reply(['error' => $msg], $code); }
function body(): array {
    $b = json_decode(file_get_contents('php://input'), true);
    if (!is_array($b)) fail('Corps JSON invalide');
    return $b;
}
function safe(string $s): string {            // pour les noms de dossiers / fichiers
    $s = preg_replace('/[^a-z0-9-]+/', '-', strtolower($s));
    return trim(substr($s, 0, 60), '-') ?: 'x';
}
function ensureDirs(): void {
    foreach ([DATA_DIR, BACKUP_DIR, IMG_DIR] as $d) {
        if (!is_dir($d) && !mkdir($d, 0775, true)) fail("Impossible de créer $d (droits ?)", 500);
    }
}

/* Enregistre des octets d'image après vérification ; renvoie le chemin public. */
function storeImage(string $bytes, string $id, string $name): string {
    if (strlen($bytes) > MAX_IMAGE_BYTES) fail('Image trop lourde');
    $info = @getimagesizefromstring($bytes);
    $ext = ['image/png' => 'png', 'image/jpeg' => 'jpg', 'image/webp' => 'webp', 'image/gif' => 'gif', 'image/avif' => 'avif'][$info['mime'] ?? ''] ?? null;
    if (!$ext) fail("Ce fichier n'est pas une image reconnue");
    $dir = IMG_DIR . '/' . safe($id);
    if (!is_dir($dir)) mkdir($dir, 0775, true);
    $file = safe($name) . '-' . date('YmdHis') . '-' . substr(md5($bytes), 0, 6) . '.' . $ext;   // nom unique : pas de souci de cache
    file_put_contents("$dir/$file", $bytes);
    return 'img/' . safe($id) . '/' . $file;
}

ensureDirs();
$action = $_GET['a'] ?? '';

switch ($action) {

case 'load':
    if (!file_exists(DATA_FILE)) {
        if (!file_exists(SEED_FILE)) fail('Aucune donnée (ni data/watches.json ni seed/watches.json)', 500);
        copy(SEED_FILE, DATA_FILE);
    }
    header('Content-Type: application/json; charset=utf-8');
    readfile(DATA_FILE);
    exit;

case 'save':
    $raw = file_get_contents('php://input');
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['watches'], $data['categories'])) fail('Données invalides : rien enregistré');
    if (file_exists(DATA_FILE)) {
        copy(DATA_FILE, BACKUP_DIR . '/watches-' . date('Ymd-His') . '.json');
        $old = glob(BACKUP_DIR . '/watches-*.json');
        sort($old);
        foreach (array_slice($old, 0, max(0, count($old) - KEEP_BACKUPS)) as $f) unlink($f);
    }
    $tmp = DATA_FILE . '.tmp';
    file_put_contents($tmp, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
    rename($tmp, DATA_FILE);                   // écriture atomique
    reply(['ok' => true, 'saved' => date('c')]);

case 'fetch':
    $b = body();
    $errors = [];
    foreach (($b['urls'] ?? []) as $url) {
        if (!preg_match('#^https?://#i', $url)) { $errors[] = "$url : adresse refusée"; continue; }
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 5,
            CURLOPT_TIMEOUT => 25, CURLOPT_CONNECTTIMEOUT => 8,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_USERAGENT => 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36',
            CURLOPT_HTTPHEADER => ['Accept: image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8'],
        ]);
        $bytes = curl_exec($ch);
        $status = curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $err = curl_error($ch);
        curl_close($ch);
        if ($bytes === false || $status >= 400 || !@getimagesizefromstring($bytes)) {
            $errors[] = "$url : " . ($err ?: "HTTP $status ou pas une image");
            continue;
        }
        reply(['src' => storeImage($bytes, $b['id'] ?? 'divers', $b['name'] ?? 'photo'), 'from' => $url]);
    }
    fail('Aucune source n\'a fonctionné — ' . implode(' | ', $errors), 502);

case 'upload':
    $b = body();
    if (!preg_match('#^data:image/[a-z+]+;base64,(.+)$#s', $b['dataUrl'] ?? '', $m)) fail('Image attendue (data URL)');
    reply(['src' => storeImage(base64_decode($m[1]), $b['id'] ?? 'divers', $b['name'] ?? 'photo')]);

default:
    fail('Action inconnue', 404);
}
