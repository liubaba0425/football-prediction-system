<?php
$API_KEY = "c7af0126df9eb35c363065dcea447d8d";
$BASE = "https://api.the-odds-api.com/v4";

// 先查支持的联赛
$sports = json_decode(file_get_contents("$BASE/sports?apiKey=$API_KEY"), true);
$australia = array_filter($sports, fn($e) => stripos($e['key'], 'australia') !== false);
foreach ($australia as $a) { echo "AU: {$a['key']} - {$a['title']}\n"; }

// 澳超
$league = "soccer_australia_aleague";
$res = file_get_contents("$BASE/sports/{$league}/odds?apiKey=$API_KEY&regions=uk,eu&markets=h2h,spreads,totals&oddsFormat=decimal&dateFormat=iso");
$data = json_decode($res, true);
echo "\n澳超比赛数: " . count($data) . "\n";

foreach ($data as $m) {
    $home = strtolower($m['home_team']);
    $away = strtolower($m['away_team']);
    if (strpos($home, 'melbourne') !== false || strpos($away, 'melbourne') !== false ||
        strpos($home, 'newcastle') !== false || strpos($away, 'newcastle') !== false) {
        echo "\n=== MATCH: {$m['home_team']} vs {$m['away_team']} ===\n";
        echo "Commence time: {$m['commence_time']}\n";
        foreach ($m['bookmakers'] as $bm) {
            echo "\n[{$bm['title']}]\n";
            foreach ($bm['markets'] as $market) {
                echo "  {$market['key']}:\n";
                foreach ($market['outcomes'] as $o) {
                    echo "    {$o['name']}: {$o['price']}\n";
                }
            }
        }
    }
}
?>
