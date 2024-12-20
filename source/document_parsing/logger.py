import os
from datetime import datetime

# 전역 변수로 로그 파일 경로 설정
LOG_FILE_PATH = None
# 토큰 사용량 기록 파일 경로
TOKEN_USAGE_FILE = "token_usage.txt"

def initialize_logger():
    """
    프로그램 실행 시 한 번만 호출되어 로그 파일을 초기화합니다.
    logs 폴더가 없으면 생성하고, 현재 시간을 기반으로 로그 파일명을 설정합니다.
    """
    global LOG_FILE_PATH
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 현재 시간으로 로그 파일명 생성 (단, 실행 시 1회만)
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        LOG_FILE_PATH = os.path.join(log_dir, f"{current_time}.log")

    except Exception as e:
        print(f"Error initializing logger: {e}")

def log_to_file(message: str):
    """
    중간처리 결과를 초기화된 로그 파일에 기록합니다.
    """
    try:
        if LOG_FILE_PATH is None:
            raise ValueError("Logger has not been initialized. Call 'initialize_logger()' first.")

        # 이미 설정된 파일에 내용 추가 (append)
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
            log_file.write(message + "\n")

    except Exception as e:
        print(f"Error logging to file: {e}")

def log_token_usage(token_count: int):
    """
    사용한 OpenAI API 토큰 개수를 기록.
    """
    try:
        # 기존 파일 읽기
        lines = []
        total_tokens = 0

        try:
            # 파일 읽기
            with open(TOKEN_USAGE_FILE, "r", encoding="utf-8") as file:
                lines = file.readlines()

            # 기존 총합 가져오기 및 제거
            updated_lines = []
            for line in lines:
                if line.startswith("총합 :"):
                    total_tokens = int(line.split(":")[1].strip())  # 기존 총합 추출
                else:
                    updated_lines.append(line)  # 총합 제외한 나머지 데이터 저장
            lines = updated_lines  # 기존 데이터를 총합 제외한 내용으로 갱신

        except FileNotFoundError:
            # 파일이 없을 경우 초기화
            pass

        # 현재 토큰 사용량 추가
        total_tokens += token_count
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_entry = f"{now} : {token_count}\n"

        # 파일 쓰기 (새로운 데이터 위로 추가)
        with open(TOKEN_USAGE_FILE, "w", encoding="utf-8") as file:
            file.write(f"총합 : {total_tokens}\n")
            file.write(new_entry)
            file.writelines(lines)

    except Exception as e:
        print(f"Error logging token usage: {e}")

def log_and_print_final_results(category, entity_structure, predicate_structure):
    """
    최종적으로 추출된 category, entity_structure, predicate_structure 배열을 로그로 출력하는 함수.
    """
    log_to_file("\n=== Category 배열 ===")
    for item in category:
        log_to_file(str(item))

    log_to_file("\n=== Entity Structure 배열 ===")
    for item in entity_structure:
        log_to_file(str(item))

    log_to_file("\n=== Predicate Structure 배열 ===")
    for item in predicate_structure:
        log_to_file(str(item))