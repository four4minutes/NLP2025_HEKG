from datetime import datetime

# 토큰 사용량 기록 파일 경로
TOKEN_USAGE_FILE = "token_usage.txt"

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