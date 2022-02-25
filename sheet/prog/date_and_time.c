#include <stdio.h>
#include <time.h>

int main(void){

/* == 型 == */
/* 時刻を示すtime_t型と、カレンダー上の日付を示すtm構造体を使用する。*/
/* 他に経過時間を示すclock_tが使用できる。 */
/* [[POSIX]] time_tではUnix時間からの秒数である。厳密には整数か浮動小数点かは未規定だが、浮動小数点での実装はないと思って良い。 */
/* 2038年問題も参照すること。 */

/* == 現在の日付と時刻 == */
time_t nowvar = time(NULL);	/* またはtime(&nowvar); */

/* == オブジェクトの生成 == */
struct tm mybirthtimetm;
/* 構造体のアイテムを直接指定 */
mybirthtimetm.tm_year = 84; /* = 1984年; 2018年は118 */
mybirthtimetm.tm_mon = 8; /* = 9月; 0-11で指定 */
mybirthtimetm.tm_mday = 24;
mybirthtimetm.tm_hour = 12;
mybirthtimetm.tm_min = 3;
mybirthtimetm.tm_sec = 24; /* 0-60で指定、60は閏秒 */
/* もしくは環境が許せば[[POSIX拡張]]のstrptimeを使用できる */
strptime("1984-09-24 12:03:24", "%Y-%m-%d %H:%M:%S", &mybirthtimetm);
/* struct tmからtime_tに変換 */
time_t mybirthtime = mktime(&mybirthtimetm); /* tm_wday(曜日)も書き換えられる */

/* == オブジェクトからのアイテムの取得 == */
/* 取得にはまずtime_tをstruct tm に変換する必要がある */
struct tm* nowtm = localtime(&nowvar);
printf("%04d-%02d-%02d %02d:%02d:%02d\n", nowtm->tm_year + 1900, nowtm->tm_mon, nowtm->tm_mday, nowtm->tm_hour, nowtm->tm_min, nowtm->tm_sec);
/* localtimeはstaticなデータへのポインタを返す。解放は不要。*/
/* 自前の変数に格納する安全な(POSIX拡張)localtime_rや(C11)localtime_s(&nowvar, &nowtm)の使用を考慮 */
/* UTCで取得する gmtime, gmtime_sも使用可能*/

/* == 曜日 == */
printf("%d\n", nowtm->tm_wday); /* Sun = 0, Mon = 1, ... */

/* == Unix time == */
/* POSIXではtime_tそのものがepochからの秒数 */
printf("%lld\n", (long long)nowvar);


/* == プロセッサー時間・高分解能時間 == */
clock_t dur = clock(); /* クロックカウンタを取得 */
printf("%lf(sec)\n", dur * 1.0 / CLOCKS_PER_SEC); /* 秒に変換 */
/* (POSIX) さらに高分解能・モノトニックなクロックも使用できる */
struct timespec ts;
clock_getres(CLOCK_REALTIME, &ts);
printf("分解能: %lld (sec.) + %ld (ns.)\n", (long long)ts.tv_sec, ts.tv_nsec);
clock_gettime(CLOCK_REALTIME, &ts);
printf("%lld (sec.) + %ld (ns.)\n", (long long)ts.tv_sec, ts.tv_nsec);
/* クロックにはCLOCK_REALTIME(Unix timeな実時間), CLOCK_REALTIME_COARSE(CLOCK_REALTIMEより早いが精度が低い), CLOCK_MONOTONIC, CLOCK_MONOTONIC_COARSE, CLOCK_MONOTONIC_RAW, CLOCK_BOOTTIME, CLOCK_PROCESS_CPUTIME_ID, CLOCK_THREAD_CPUTIME_IDが指定できる。 */


/* == 時間の計算 == */
double delta = difftime(nowvar, mybirthtime); /* (秒) */
/* 単純な引き算(mybirthtime - nowvar)と違い、POSIX環境でなくても使用可能(POSIX以外ではtime_tが秒単位とは限らない) */

/* == 時差情報 == */
struct tm *birthdate_gmtm = gmtime(&mybirthtime);
/* 安全なgmtime_rやgmtime_s(time_t*, struct tm*)を推奨*/
/* それ以上のタイムゾーン処理は、標準ライブラリのみでは難しい*/

/* == 文字列へ == */
printf("%s", ctime(&mybirthtime)); /* time_t -> 文字列 */
printf("%s", asctime(&mybirthtimetm)); /* struct tm -> 文字列 */
/* [[C11]] 安全なctime_s, asctime_sを推奨 */
char buf[256];
strftime(buf, sizeof buf, "%Y-%m-%d %H:%M:%S", &mybirthtimetm);
printf("%s\n", buf);

	return 0;
}

