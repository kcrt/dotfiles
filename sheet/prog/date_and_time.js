
// == 型 ==
// 標準オブジェクトとしてDateが利用可能である


// == 現在の日付と時刻 ==
nowvar = new Date(); // 現在の日付

// == オブジェクトの生成 ==
mybirthday = new Date(1984, 8, 24); // 注：9月です。月は0-11
mybirthtime = new Date(1984, 8, 24, 12, 3, 24);
mybirthtime = new Date('September 24, 1984 12:03:24'); // 非推奨: ブラウザごとに挙動が異なる
// new なしで呼び出した`Date(1984, 9, 24)`場合は文字列を返すので注意

// == オブジェクトからのアイテムの取得
console.log(mybirthtime.getFullYear(), mybirthtime.getMonth(), mybirthtime.getDate(),
            mybirthtime.getHours(), mybirthtime.getMinutes(), mybirthtime.getSeconds(),
            mybirthtime.getMilliseconds());
// mybirthtime.getMonth()は8 (=9月)
// mybirthtime.getYear()は非推奨

// == 曜日 ==
mybirthtime.getDay(); // Sun = 0, Mon = 1, ...

// == Unix time [ミリ秒単位] ==
Date.now(); // 現在の時刻 (Unix time)
birth_epoch = mybirthtime.getTime(); // Unix timeに変換
new Date(birth_epoch); // Unix timeから

// == プロセッサー時間・高分解能時間 ==
// performance.now()が高分解能・モノトニックであるがサポートされていない環境も多い
// Node.jsではprocess.hrtime()が[秒, ナノ秒]を返す

// == 時間の計算 ==
delta = mybirthtime - nowvar; // Dateの差はミリ秒で取得できる
mybirthtime.setMonth(mybirthtime.getMonth() + 10); // 10ヶ月後
// setMonthは負の数や12以上の数もうまく処理してくれるので、
// それを利用して日付や時刻の計算を行える


// == 時差関連 == 
// mybirthtime.getUTCHours()などで協定世界時に基づく値を取得できる
mybirthtime.getTimezoneOffset(); // 時差(分): 日本だと -540(+9hだがマイナス)

// == 文字列へ ==
mybirthtime.toDateString(); // 日付部のみ 'Mon Sep 24 1984'
mybirthtime.toTimeString(); // 時刻部のみ '12:03:24 GMT+0900 (JST)'
mybirthtime.toString(); // 'Mon Sep 24 1984 12:03:24 GMT+0900 (JST)'
mybirthtime.toLocaleString(); // 設定に沿った表記 '1984/9/24 12:03:24'
    // toLocaleDateString(), toLocalTimeString()もあり
mybirthtime.toISOString(); // ISO形式(UTC時間) '1984-09-24T03:03:24.000Z'
mybirthtime.toUTCString(); // 'Mon, 24 Sep 1984 03:03:24 GMT'
new Intl.DateTimeFormat().format(nowvar);		// デフォルト
new Intl.DateTimeFormat("ar-EG").format(nowvar);	// アラビア語
new Intl.DateTimeFormat("en-US", {hour12: false, weekday: "long"}).format(nowvar);
// toLocaleFormatは非推奨
