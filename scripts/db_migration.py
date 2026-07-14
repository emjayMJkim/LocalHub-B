import sqlite3
import json
import glob
import os

# 현재 스크립트 위치 기준 경로 설정
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPTS_DIR)

# DB 파일 생성 경로 (루트 디렉토리에 생성)
DB_PATH = os.path.join(ROOT_DIR, 'localhub.db')

# JSON 파일 검색 경로 (data 폴더 내에서 검색)
DATA_DIR = os.path.join(ROOT_DIR, 'data')
json_files = glob.glob(os.path.join(DATA_DIR, '대전_충청권_*.json'))

def create_tables(cursor):
    """
    일반 데이터 테이블과 FTS5 검색용 가상 테이블을 생성합니다.
    """
    # 1. 원본 데이터를 저장할 일반 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            contentid TEXT PRIMARY KEY,
            region TEXT,
            contentType TEXT,
            title TEXT,
            addr1 TEXT,
            addr2 TEXT,
            zipcode TEXT,
            tel TEXT,
            mapx REAL,
            mapy REAL,
            mlevel TEXT,
            firstimage TEXT,
            firstimage2 TEXT,
            createdtime TEXT,
            modifiedtime TEXT
        )
    ''')

    # 2. 자연어 검색(Full-Text Search)을 위한 FTS5 가상 테이블
    # tokenize='unicode61'은 한글/영문 검색에 무난하게 작동하는 기본 토크나이저입니다.
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS places_fts USING fts5(
            contentid UNINDEXED,
            title,
            addr1,
            contentType,
            region,
            tokenize='unicode61'
        )
    ''')

def insert_data(cursor, region, content_type, items):
    """
    JSON의 items 배열을 DB에 삽입합니다.
    """
    insert_query = '''
        INSERT OR REPLACE INTO places (
            contentid, region, contentType, title, addr1, addr2, 
            zipcode, tel, mapx, mapy, mlevel, firstimage, firstimage2, 
            createdtime, modifiedtime
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    fts_insert_query = '''
        INSERT INTO places_fts (contentid, title, addr1, contentType, region)
        VALUES (?, ?, ?, ?, ?)
    '''

    for item in items:
        # mapx, mapy가 빈 문자열일 경우 0.0으로 처리
        mapx = float(item.get('mapx')) if item.get('mapx') else 0.0
        mapy = float(item.get('mapy')) if item.get('mapy') else 0.0

        # 일반 테이블 Insert
        cursor.execute(insert_query, (
            item.get('contentid', ''),
            region,
            content_type,
            item.get('title', ''),
            item.get('addr1', ''),
            item.get('addr2', ''),
            item.get('zipcode', ''),
            item.get('tel', ''),
            mapx,
            mapy,
            item.get('mlevel', ''),
            item.get('firstimage', ''),
            item.get('firstimage2', ''),
            item.get('createdtime', ''),
            item.get('modifiedtime', '')
        ))

        # FTS5 가상 테이블 Insert (검색 최적화)
        cursor.execute(fts_insert_query, (
            item.get('contentid', ''),
            item.get('title', ''),
            item.get('addr1', ''),
            content_type,
            region
        ))

def main():
    # 1. DB 연결
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 2. 테이블 생성
    print("데이터베이스 테이블 생성 중...")
    create_tables(cursor)

    # 3. 대상 JSON 파일 목록 검색
    json_files = glob.glob('대전_충청권_*.json')
    
    if not json_files:
        print("경고: 현재 디렉토리에서 '대전_충청권_*.json' 파일을 찾을 수 없습니다.")
        return

    # 4. 파일별 파싱 및 적재
    total_inserted = 0
    for file_path in json_files:
        print(f"[{os.path.basename(file_path)}] 적재 중...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            region = data.get('region', '')
            content_type = data.get('contentType', '')
            items = data.get('items', [])
            
            insert_data(cursor, region, content_type, items)
            total_inserted += len(items)

    # 5. DB 커밋 및 종료
    conn.commit()
    conn.close()
    
    print(f"\\n완료! 총 {total_inserted}건의 데이터가 '{DB_PATH}'에 성공적으로 적재되었습니다.")
    print("이제 'SELECT * FROM places_fts WHERE places_fts MATCH \"검색어\"' 쿼리로 FTS5 검색이 가능합니다.")

if __name__ == '__main__':
    main()