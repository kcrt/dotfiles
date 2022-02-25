#include <stdio.h>
#include <string.h>
#include <stdlib.h>


int compare_int(const void* a, const void* b){

	if(*(const int *) a < *(const int *)b){
		return -1;
	}else if(*(const int *) a > *(const int *)b){
		return 1;
	}else{
		return 0;
	}

}

int main(int argc, char** argv){

	// 通常の配列型 (C言語と同じ)
	int arr[] = {1, 3, 4, 2, 5};		// 要素数は省略できる
	printf("%d %zu %ld\n",
			arr[0],
			sizeof(arr),	// 配列のサイズ(byte)
			sizeof(arr) / sizeof(arr[0]));	// 個数

	// C言語で配列を扱うには、ポインタの知識が必須になる
	// 100個のintを確保して初期化
	int *m;
	m = (int *)malloc(sizeof(int) * 100);	// stdlib
	memset(m, 0, sizeof(arr));	// string.h

	// arrをコピー
	memcpy(m, arr, sizeof(arr));
	
	// arrをソート
	qsort(arr, sizeof(arr) / sizeof(arr[0]),
			sizeof(int), compare_int);
	for(int i = 0; i < 5; i++)
		printf("%d ", arr[i]);
	
	free(m);

	printf("Hello, world!\n");
	return 0;

}

// gcc helloworld.c -o helloworld(実行ファイル名)
// clang helloworld.c -o helloworld
