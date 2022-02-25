#include <stdio.h>
#include <unistd.h>		/* getopt [[POSIX]] */
int main(int argc, char** argv){

	/* argv[0], argv[1], ..., argv[argc-1]で引数にアクセス */
	/* argv[0]は実行中のプログラム名 */
	printf("%s\n", argv[0]);

	/* 引数の解釈は自分で行うか、getopt [[POSIX]] を利用する。 */
	/*
	 * int getopt(int argc, char * const argv[], const char *optstring);
	 * extern char *optarg;
	 * extern int opterr, optind, optopt;
	 */

	char c;
	while((c = getopt(argc, argv, "abc:") ) != -1){
		switch(c) {
			case 'a':
				printf("-a specified\n");
				break;
			case 'b':
				printf("-b specified\n");
				break;
			case 'c':
				printf("-c with %s\n", optarg);
				break;
		}
	}

	/* optstring - "abc:" だと、a, b, オプション付きc (:でオプション付き)
	 * ":"で始める(例: ":abc:")にすると、getoptは
	 *   ':' - オプションの指定がない
	 *   '?' - 不明な引数
	 * を返すようになる
	 */

	/* これ以上の動作を行いたいときは、getopt_long [[GNU]] などを使用することになる。 */
}
