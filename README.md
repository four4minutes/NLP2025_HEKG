# NLP2025_HEKG
言語処理学会第31回年次大会 (NLP2025) で発表した論文で使用されたプログラムを公開するものである。本プログラムは、失敗知識データベース [1] に掲載されている文書を分析し、階層的構造を持つナレッジグラフ (Knowledge Graph) を構築する。データベースにはグラフデータベースである [neo4j community edition][2] を利用する。ナレッジグラフの詳細や実装方法については発表論文をご参照ください。本プログラムは Python で実装されている。

## 利用方法
本プログラムは Python 3.9 で動作確認を行っている。
### scraper
失敗知識データベース」の各ウェブページをスクレイピングし、取得したHTMLをJSON形式のデータセットとしてローカルに保存する。  
必要なPythonパッケージ : BeautifulSoup4, requests  
```bash
pip install beautifulsoup4 requests
```
scrape_database.py を実行すると、同じディレクトリ（または設定によって指定されたパス）にスクレイピング結果のデータセットが生成される。  
```bash
python source/scraper/scrape_database.py
```
実行前に、以下の変数を設定できる。
```python title="./source/scraper/scrape_datebase.py"
root_folder_name = "失敗知識データベース" # 出力される最終的なデータセットのフォルダ名

main_page_url = "https://www.shippai.org/fkd/index.php"  # メインページのURL
base_url = "https://www.shippai.org/fkd"  # 下位ページで共通となるURLの部分
```

### document parsing
必要なPythonパッケージ : OpenAI API, Sentence Transformers
```bash
pip install openai sentence-transformers
```


## 発表文献
[論文本文](https://www.anlp.jp/proceedings/annual_meeting/2025/pdf_dir/B7-2.pdf)

## 関連・参考文献
[1] 失敗知識データベース https://www.shippai.org/fkd/index.php  
[2] neo4j community edition https://github.com/neo4j/neo4j

## ライセンス(Licensing)
NLP2025_HEKGはMIT Licenseの下で公開されているオープンソースプロジェクトである。  
NLP2025_HEKG is an open source licensed under the MIT License.