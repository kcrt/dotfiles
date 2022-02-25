#include <chrono>
#include <ctime>
#include <iostream>
#include <sstream>
#include <iomanip>
using namespace std::chrono;
using namespace std;

int main (){

// == 型 ==
// 時間の長さを示すdurationと、時刻を示すtime_pointを使用する。
// durationの別名として、hours, minutes, secondsなどを使用できる。

// == 現在の日付と時刻 ==
system_clock::time_point nowvar = system_clock::now();

// == オブジェクトの生成 ==
// 直接生成することは難しい。
// (C++11) get_timeとC言語のstruct tmを経由するのが簡単。
// (C++20) std::chrono_literalsで構築ができるようになる予定
struct tm t;
istringstream ss("1984-09-24 12:03:24");
ss >> get_time(&t, "%Y-%m-%d %H:%M:%S");
auto mybirthtime_timet = mktime(&t);
auto mybirthtime = system_clock::from_time_t(mybirthtime_timet);

// == オブジェクトからのアイテムの取得 ==
// C++20が使用できるようになるまではあまり良い方法がない。
// to_time_t()で変換し、古き良き構文を使用するのが簡単。

// == 曜日 ==
// C++20からweekdayが追加される予定。

// == Unix time ==
// C++20からepochは1970/1/1 00:00:00だが、それ以前は未規定。ただし、殆どの処理系はUnix timeです。
auto birth_epoch = system_clock::to_time_t(mybirthtime);
    // time_tにする
auto birth_epoch2 = mybirthtime.time_since_epoch();
    // epochからのdurationに変換する

// == プロセッサー時間・高分解能時間 ==
steady_clock::now();    // モノトニック
high_resolution_clock::now();  // 高分解能
// C++20からはgps_clockやfile_clockなどが追加される予定

// == 時間の計算 ==
auto delta = nowvar - mybirthtime; // 差でdurationを取得
auto hrs = duration_cast<hours>(delta); // それは何時間？
std::cout << hrs.count();

using namespace std::literals::chrono_literals;
auto after_onehalf_hour = nowvar + 1.5h; // C++14

// == 時差情報 ==
// C++20よりタイムゾーンサポートが追加される予定

// == 文字列へ ==
// C++20よりcout<<とフォーマットが追加される予定

    return 0;
}
