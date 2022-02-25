#include <stdio.h>

int main(int argc, char** argv){

	// if
	int a = 10;
	if (a < 10){
		printf("less than 10.\n");
	}else if (a == 10){
		printf("equal to 10.\n");
	}else{
		// 何もしないときは何も入れなくて良い
	}

	// ブロックを使用せずに単文を使用することも出来る。
	if (a == 10)
		printf("a is 10!\n");

	// for
	// for (初期化節; 条件; 繰り返し文)
	// 初期化節で宣言した変数はfor内のみで有効 [[C99]]
	for (int i = 0; i < 5; i++){
		printf("%d\n", i);	// 0 1 2 3 4
	}

	// break, continue
	for (int i = 0; i < 5; i++){
		if (i == 4){
			continue;
		}else if(i == 5){
			break;
		}
	}

	// infinite loop
	for(;;){
		break;
	}
	
	for(int i = 0; i < 5; i++){
		int i = 1;	// Cでは動作する [[C/C++]]
		printf("%d\n", i);
	}

	// foreach はない
	
	// loop
	while (a > 0){
		a--;
	}

	while (a < 10){
		a++;
		if (a == 4) continue;
		if (a == 6) break;
	}

	do {
		a--;
	} while (a < 0);

	// switch (select case)
	switch(a){					// 整数, enumのみ可
		case 0:
			printf("zero\n");
			break;
		case 1:
			printf("two\n");	// break忘れるとfallthrough[[注意]]
		//case a:					// 定数でないといけない
		//	printf("invalid!");
		default:
			printf("other\n");	// それ以外の場合
	}

// goto
	goto mylabel;
mylabel:

	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
