# NLP2025_HEKG
本プログラムは、言語処理学会第31回年次大会(NLP2025)で発表した論文に基づき作成されたプログラムである。失敗知識データベース[1]に記載された文書をもとに、階層的構造を持つナレッジグラフ(Knowledge Graph)を構築する。データベースにはグラフDBであるneo4j community edition[2]を利用する。プログラムの詳細や実装については、発表文献を参照のこと。

## 利用方法
### scraper

### document parsing

### graph embedding

### re_structuring


## ソースコードに関する簡単な説明
### scraper
失敗知識データベースのウェブページから情報を収集し、それをjson形式に変換して保存する。
1. scrape_database.py: データベース全体を対象とした収集処理を制御する。
2. scrape_multiple_pages.py: 失敗知識データベースの分野別ページから下位ページへの接続を制御する。
3. scrape_to_json.py: ウェブページの文書を実際にjson形式に変換する。

### document_parsing
json形式の文書を分析し、ナレッジグラフに埋め込む準備を行う。
1. read_json.py: jsonファイルを読み込み、上から順に必要な処理を実行する。
2. time_and_place_extraction.py: 文中から時間と場所を表す表現を抽出する。
3. predicate_extraction.py: 文中の述語を抽出し、その情報を基に述語項構造を構築する。
4. token_logger.py: OpenAI APIのトークン使用量を記録する。
5. causal_relationship_extraction.py: 文中の因果関係を抽出する。
6. residue_extraction.py: 未認識の内容を確認するための処理を行う。

### graph_embedding
分析結果に基づき、グラフDBへのデータ埋め込みを行う。

### re_structuring
構築されたナレッジグラフの既存構造を保持しつつ、再構築を行う。

## 発表文献
発表予定

## 関連・参考文献
[1] 失敗知識データベース https://www.shippai.org/fkd/index.php
[2] neo4j community edition https://github.com/neo4j/neo4j

## ライセンス(Licensing)
NLP2025_HEKGはMIT Licenseの下で公開されているオープンソースプロジェクトである。
NLP2025_HEKG is an open source licensed under the MIT License.