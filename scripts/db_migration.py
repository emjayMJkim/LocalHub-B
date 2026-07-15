import sqlite3
import json
import glob
import os

def create_tables(cursor):
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

    # 2. 위경도 복합 인덱스 생성
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_places_coordinates 
        ON places (mapx, mapy)
    ''')

    # 3. Trigram 토크나이저를 적용한 FTS5 가상 테이블
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS places_fts USING fts5(
            contentid UNINDEXED,
            title,
            addr1,
            contentType,
            region,
            tokenize='trigram'
        )
    ''')

def insert_data(cursor, region, content_type, items):
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
        mapx = float(item.get('mapx')) if item.get('mapx') else 0.0
        mapy = float(item.get('mapy')) if item.get('mapy') else 0.0

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

        cursor.execute(fts_insert_query, (
            item.get('contentid', ''),
            item.get('title', ''),
            item.get('addr1', ''),
            content_type,
            region
        ))

def main():
    # 경로 설정
    SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(SCRIPTS_DIR)
    
    # DB 파일 생성 경로 (루트 디렉토리에 생성)
    db_path = os.path.join(ROOT_DIR, 'localhub.db')
    
    # JSON 파일 검색 경로 (data 폴더 내에서 검색)
    data_dir = os.path.join(ROOT_DIR, 'data')
    json_files = glob.glob(os.path.join(data_dir, '대전_충청권_*.json'))
    
    print(f"DEBUG: 데이터 파일 {len(json_files)}개를 찾았습니다.")

    # DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 생성
    create_tables(cursor)

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

    conn.commit()
    conn.close()
    print(f"\n완료! 총 {total_inserted}건의 데이터가 적재되었습니다.")

if __name__ == '__main__':
    main()