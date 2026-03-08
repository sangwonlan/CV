import re

SKILL_REJECT_SUBSTRINGS = (
    "으로 ",
    "에서 ",
    "후 ",
    "위한 ",
    "경험",
    "사례",
    "반영",
    "제작",
    "상세",
    "자동 ",
    "기반 ",
    "설계",
    "숙지",
    "이론",
    "로드맵",
    "필요한",
    "보완",
    "자기소개서",
    "구현",
)

SKILL_REJECT_EXACT = {
    "스위핑",
    "홈 페그보드",
    "페그보드",
    "fma",
    "wmft",
    "copm",
    "msrt",
    "moca",
    "mmse",
}

UPPERCASE_SKILL_ALLOWLIST = {
    "AI",
    "API",
    "AWS",
    "CSS",
    "ETL",
    "GPT",
    "HTML",
    "IT",
    "LLM",
    "ML",
    "NLP",
    "R",
    "SAS",
    "SQL",
    "UI",
    "UX",
}

def parse_portfolio_text(text):
    """
    포트폴리오 텍스트를 섹션별로 파싱하여 딕셔너리로 반환.

    반환 형식:
    {
        "profile": {"name": "", "school": "", "major": "", "status": ""},
        "experiences": [{"company": "", "period": "", "role": "", "description": ""}],
        "practicals": [{"name": "", "organization": "", "period": "", "description": ""}],
        "projects": [{"name": "", "period": "", "tech_stack": "", "role": "", "description": ""}],
        "skills": ["Python", "React", ...],
        "certifications": [{"name": "", "date": ""}],
        "activities": [{"name": "", "period": "", "description": ""}],
        "strengths": "자유 텍스트",
    }
    """
    result = {
        "profile": {"name": "", "school": "", "major": "", "status": ""},
        "experiences": [],
        "practicals": [],
        "projects": [],
        "skills": [],
        "certifications": [],
        "activities": [],
        "strengths": "",
        "weaknesses": "",
    }

    # 섹션별로 텍스트 분리
    sections = split_into_sections(text)
    free_text = sections.get("기타", "").strip()

    for title, content in sections.items():
        title_lower = title.strip().lower()

        if match_section(title_lower, ["기본 정보", "기본정보", "인적사항"]):
            result["profile"] = parse_profile(content)

        elif match_section(title_lower, ["임상 경험", "임상경험"]):
            result["practicals"].extend(parse_practicals(content))

        # 연구/프로젝트를 경력보다 먼저 체크 ("연구 경력"이 "경력"에 잘못 매칭되지 않도록)
        elif match_section(title_lower, ["연구", "프로젝트", "연구 경력", "연구경력", "연구 내용", "창업"]):
            result["projects"].extend(parse_projects(content))

        elif match_section(title_lower, ["실습", "실습/경험", "견학"]):
            result["practicals"].extend(parse_practicals(content))

        elif match_section(title_lower, ["경력", "인턴", "직장", "근무"]):
            result["experiences"].extend(parse_experiences(content))

        elif match_section(title_lower, ["기술", "스킬", "기술 역량", "기술역량", "기술 스택"]):
            result["skills"].extend(parse_skills(content))

        elif match_section(title_lower, ["자격증", "수상", "교육", "대회"]):
            result["certifications"].extend(parse_certifications(content))

        elif match_section(title_lower, ["활동", "봉사", "리더십", "대외활동", "대외"]):
            result["activities"].extend(parse_activities(content))

        elif match_section(title_lower, ["성격", "강점", "가치관", "핵심 서사", "핵심서사"]):
            existing = result["strengths"]
            if existing:
                result["strengths"] = existing + "\n\n" + content.strip()
            else:
                result["strengths"] = content.strip()

        elif match_section(title_lower, ["단점", "보완점", "약점"]):
            existing = result["weaknesses"]
            if existing:
                result["weaknesses"] = existing + "\n\n" + content.strip()
            else:
                result["weaknesses"] = content.strip()

        elif match_section(title_lower, ["보완", "로드맵"]):
            existing = result["weaknesses"]
            if existing:
                result["weaknesses"] = existing + "\n\n" + content.strip()
            else:
                result["weaknesses"] = content.strip()

        elif match_section(title_lower, ["보유 서류"]):
            pass

    if free_text:
        if result["strengths"]:
            result["strengths"] = result["strengths"] + "\n\n" + free_text
        elif not has_any_parsed_content(result):
            # 섹션이 거의 없는 자유 서술형 입력은 강점/가치관 임시 보관으로 처리한다.
            result["strengths"] = free_text

    return result


def has_any_parsed_content(result):
    return (
        any(result["profile"].values())
        or bool(result["experiences"])
        or bool(result["practicals"])
        or bool(result["projects"])
        or bool(result["skills"])
        or bool(result["certifications"])
        or bool(result["activities"])
        or bool(result["strengths"].strip())
        or bool(result["weaknesses"].strip())
    )


def match_section(title, keywords):
    """제목이 키워드 목록 중 하나라도 포함하면 True"""
    for kw in keywords:
        if kw.lower() in title:
            return True
    return False


def split_into_sections(text):
    """
    텍스트를 섹션 제목 기준으로 분리.
    제목 패턴: 줄 시작에 오는 한글 제목 (숫자. 또는 # 또는 ** 등으로 시작)
    """
    sections = {}

    # 다양한 헤더 패턴 감지
    # "# 제목", "## 제목", "**제목**", "제목\n", 숫자. 제목 등
    header_pattern = re.compile(
        r'^(?:#{1,3}\s+|(?:\*\*)|(?:\d+\.\s*))?\s*'
        r'([\w\s/·()（）\-\+]+?)(?:\*\*)?\s*$',
        re.MULTILINE
    )

    # 실제 섹션 분리를 위해 명시적 키워드 기반으로 분리
    known_sections = [
        "기본 정보", "기본정보", "인적사항",
        "임상 경험", "임상경험",
        "연구 경력", "연구경력", "연구 내용 상세", "연구내용",
        "창업 및 실용화", "창업",
        "수상 및 대회", "수상",
        "자격증 및 교육", "자격증",
        "기술 역량", "기술역량", "기술 스택",
        "리더십 및 대외활동", "리더십", "대외활동",
        "현재 보유 서류", "보유 서류",
        "핵심 서사",
        "보완이 필요한 사항", "보완",
        "경력", "인턴",
        "실습", "프로젝트",
        "성격", "강점", "가치관",
        "활동", "봉사",
        "목표",
    ]

    # 텍스트를 줄 단위로 스캔하며 섹션 분리
    lines = text.split("\n")
    current_section = "기타"
    current_content = []

    for line in lines:
        stripped = line.strip()
        # 빈 줄은 그대로 추가
        if not stripped:
            current_content.append("")
            continue

        # 헤더인지 확인
        clean = re.sub(r'^[#*\d.\s\-]+', '', stripped).strip()
        clean = re.sub(r'\*+$', '', clean).strip()

        is_header = False
        for section_name in known_sections:
            if section_name in clean and len(clean) < 30:
                is_header = True
                # 이전 섹션 저장
                if current_content:
                    content_text = "\n".join(current_content).strip()
                    if content_text:
                        if current_section in sections:
                            sections[current_section] += "\n\n" + content_text
                        else:
                            sections[current_section] = content_text
                current_section = clean
                current_content = []
                break

        if not is_header:
            current_content.append(line)

    # 마지막 섹션 저장
    if current_content:
        content_text = "\n".join(current_content).strip()
        if content_text:
            if current_section in sections:
                sections[current_section] += "\n\n" + content_text
            else:
                sections[current_section] = content_text

    return sections


def parse_profile(content):
    """기본 정보 파싱"""
    profile = {"name": "", "school": "", "major": "", "status": ""}

    for line in content.split("\n"):
        line = line.strip().lstrip("*-• ")

        if "이름" in line and ":" in line:
            profile["name"] = line.split(":", 1)[1].strip()
        elif "소속" in line and ":" in line:
            val = line.split(":", 1)[1].strip()
            # "연세대학교 작업치료학과 (2021학번, 현재 3학년)" 같은 형태
            parts = val.split("(")
            if parts:
                school_major = parts[0].strip()
                # 학교와 전공 분리
                words = school_major.split()
                if len(words) >= 2:
                    profile["school"] = words[0]
                    profile["major"] = " ".join(words[1:])
                else:
                    profile["school"] = school_major
            if len(parts) > 1:
                profile["status"] = parts[1].rstrip(")")
        elif "학교" in line and ":" in line:
            profile["school"] = line.split(":", 1)[1].strip()
        elif "전공" in line and ":" in line:
            profile["major"] = line.split(":", 1)[1].strip()
        elif "상태" in line and ":" in line or "학년" in line and ":" in line:
            profile["status"] = line.split(":", 1)[1].strip()

    return profile


def parse_experiences(content):
    """경력/인턴 파싱"""
    experiences = []
    current = None

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # 숫자. 제목 (기간) 패턴 또는 ### 제목 패턴
        period_match = re.search(r'\(([^)]*\d{4}[^)]*)\)', stripped)

        if (stripped.startswith(("###", "**")) or re.match(r'^\d+\.', stripped)) and period_match:
            if current:
                experiences.append(current)
            clean_name = re.sub(r'^[\d.#*\s]+', '', stripped)
            clean_name = re.sub(r'\([^)]*\d{4}[^)]*\)', '', clean_name)
            clean_name = re.sub(r'\*+', '', clean_name).strip()
            current = {
                "company": clean_name,
                "period": period_match.group(1),
                "role": "",
                "description": "",
            }
        elif current:
            clean = stripped.lstrip("*-• ")
            if "역할" in clean and ":" in clean:
                current["role"] = clean.split(":", 1)[1].strip()
            elif "담당" in clean and ":" in clean:
                current["role"] = clean.split(":", 1)[1].strip()
            else:
                if current["description"]:
                    current["description"] += "\n" + clean
                else:
                    current["description"] = clean

    if current:
        experiences.append(current)

    return experiences


def parse_practicals(content):
    """실습/경험 파싱"""
    practicals = []
    current = None
    sub_items = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # "1. 삼성서울병원 임상 실습 (2025.12.29 ~ 2026.02.20)" 같은 패턴
        period_match = re.search(r'\(([^)]*\d{4}[^)]*)\)', stripped)

        is_header = (
            (re.match(r'^\d+\.', stripped) or stripped.startswith("###") or stripped.startswith("**"))
            and period_match
        )

        if is_header:
            if current:
                current["description"] = "\n".join(sub_items)
                practicals.append(current)

            clean_name = re.sub(r'^[\d.#*\s]+', '', stripped)
            clean_name = re.sub(r'\([^)]*\d{4}[^)]*\)', '', clean_name)
            clean_name = re.sub(r'\*+', '', clean_name).strip()

            # 기관명 추출 시도 (이름에서)
            org = ""
            name = clean_name
            # "삼성서울병원 임상 실습" → org=삼성서울병원, name=임상 실습
            words = clean_name.split()
            if len(words) >= 2:
                # 첫 단어가 기관명일 가능성
                if any(kw in words[0] for kw in ["병원", "센터", "학회", "기관", "원", "재단"]):
                    org = words[0]
                    name = " ".join(words[1:])
                else:
                    # 전체를 이름으로
                    for i, w in enumerate(words):
                        if any(kw in w for kw in ["병원", "센터", "학회", "기관", "원", "재단"]):
                            org = " ".join(words[:i+1])
                            name = " ".join(words[i+1:]) if i+1 < len(words) else clean_name
                            break

            current = {
                "name": name if name else clean_name,
                "organization": org,
                "period": period_match.group(1),
                "description": "",
            }
            sub_items = []
        elif current:
            clean = stripped.lstrip("*-• ")
            if clean:
                sub_items.append(clean)

    if current:
        current["description"] = "\n".join(sub_items)
        practicals.append(current)

    return practicals


def parse_projects(content):
    """프로젝트/연구 파싱"""
    projects = []
    current = None
    sub_items = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        # 서브 헤더 감지: "보상 움직임 연구 (박케서린 교수님 연구실, 2025 1학기)"
        # 또는 테이블 형태의 연구 목록
        period_match = re.search(r'\(([^)]*(?:\d{4}|학기)[^)]*)\)', stripped)

        # 주요 헤더 패턴
        is_header = False
        if period_match and not stripped.startswith(("*", "-", "•")):
            is_header = True
        elif re.match(r'^(?:#{1,3}|(?:\d+\.)|(?:\*\*))', stripped) and len(stripped) < 100:
            is_header = True

        # 테이블 행 감지 (순번 | 학회 | 제목 | ... 형태)
        if "|" in stripped or "\t" in stripped:
            # 테이블 데이터 → 연구 항목으로 변환
            parts = re.split(r'[|\t]', stripped)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 3 and any(c.isdigit() for c in parts[0]):
                # 순번이 있는 행
                proj = {
                    "name": parts[2] if len(parts) > 2 else parts[1],
                    "period": parts[-1] if re.search(r'\d{4}', parts[-1]) else "",
                    "tech_stack": "",
                    "role": parts[1] if len(parts) > 2 else "",  # 학회명 등
                    "description": " / ".join(parts[3:-1]) if len(parts) > 4 else "",
                }
                projects.append(proj)
            continue

        if is_header and period_match:
            if current:
                current["description"] = "\n".join(sub_items)
                projects.append(current)

            clean_name = re.sub(r'^[\d.#*\s]+', '', stripped)
            clean_name = re.sub(r'\([^)]*\)', '', clean_name)
            clean_name = re.sub(r'\*+', '', clean_name).strip()

            current = {
                "name": clean_name,
                "period": period_match.group(1),
                "tech_stack": "",
                "role": "연구원",
                "description": "",
            }
            sub_items = []
        elif current:
            clean = stripped.lstrip("*-• ")
            if clean:
                sub_items.append(clean)

    if current:
        current["description"] = "\n".join(sub_items)
        projects.append(current)

    return projects


def normalize_skill_name(skill):
    clean = skill.strip()
    clean = re.sub(r'^[>\-*•\d.\s`]+', '', clean)
    clean = clean.replace("**", "").replace("__", "").replace("`", "")
    clean = re.sub(r'\s+', ' ', clean).strip(" ,;:/()[]")
    if "(" in clean:
        base = clean.split("(", 1)[0].strip()
        if base:
            clean = base
    return clean


def is_valid_skill_name(skill):
    if not skill:
        return False
    if len(skill) > 24:
        return False
    if skill.count(" ") > 3:
        return False
    if ":" in skill or "->" in skill:
        return False
    if re.search(r'[.!?]', skill):
        return False
    if skill.casefold() in SKILL_REJECT_EXACT:
        return False
    if any(token in skill for token in SKILL_REJECT_SUBSTRINGS):
        return False
    if re.fullmatch(r'[A-Z]{2,5}', skill) and skill not in UPPERCASE_SKILL_ALLOWLIST:
        return False
    return True


def normalize_skills(skills):
    normalized = []
    seen = set()

    for raw in skills:
        for part in re.split(r'[,、，/·]', raw):
            clean = normalize_skill_name(part)
            if not is_valid_skill_name(clean):
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(clean)

    return normalized


def parse_skills(content):
    """기술 스택 파싱"""
    candidates = []

    for line in content.split("\n"):
        stripped = line.strip().lstrip("*-• ")
        if not stripped:
            continue

        if ":" in stripped:
            _, items_str = stripped.split(":", 1)
            candidates.extend(re.split(r'[,、，/·]', items_str))
        else:
            candidates.extend(re.split(r'[,、，/·]', stripped))

    return normalize_skills(candidates)


def parse_certifications(content):
    """자격증/수상 파싱"""
    certs = []

    for line in content.split("\n"):
        stripped = line.strip().lstrip("*-• ")
        if not stripped:
            continue

        # "항목 | 상세 | 시기" 테이블 헤더 건너뛰기
        if stripped.startswith("항목") or stripped.startswith("수상") or stripped.startswith("---"):
            continue

        # 테이블 행
        if "|" in stripped or "\t" in stripped:
            parts = re.split(r'[|\t]', stripped)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                name = parts[0]
                # 상세 정보가 있으면 이름에 합치기
                if len(parts) >= 3:
                    desc = parts[1]
                    date = parts[2] if re.search(r'\d{4}', parts[2]) else parts[-1]
                    name = f"{name} - {desc}" if desc else name
                else:
                    date = parts[1] if re.search(r'\d{4}', parts[1]) else ""

                if name and not name.startswith("---"):
                    certs.append({"name": name, "date": date})
            continue

        # "ADsP (데이터분석 준전문가) 자격증 취득 2024.11" 형태
        date_match = re.search(r'(\d{4}[.\-/]\d{1,2}(?:[.\-/]\d{1,2})?|\d{4})', stripped)
        if date_match:
            name = stripped[:date_match.start()].strip()
            date = date_match.group(1)
            if name:
                certs.append({"name": name, "date": date})

    return certs


def parse_activities(content):
    """활동/봉사 파싱"""
    activities = []
    current = None
    sub_items = []

    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        clean = stripped.lstrip("*-• ")

        # "학술 봉사 동아리 '우리' 회장 (우리장, 2022):" 같은 패턴
        period_match = re.search(r'\(([^)]*\d{4}[^)]*)\)', clean)

        if period_match and ":" in clean:
            if current:
                current["description"] = "\n".join(sub_items)
                activities.append(current)

            name = clean[:clean.index("(")].strip()
            desc_start = clean.index(":") + 1
            first_desc = clean[desc_start:].strip()

            current = {
                "name": name,
                "period": period_match.group(1),
                "description": "",
            }
            sub_items = [first_desc] if first_desc else []
        elif period_match and len(clean) < 80:
            if current:
                current["description"] = "\n".join(sub_items)
                activities.append(current)

            name = re.sub(r'\([^)]*\)', '', clean).strip()
            current = {
                "name": name,
                "period": period_match.group(1),
                "description": "",
            }
            sub_items = []
        elif current:
            if clean:
                sub_items.append(clean)
        else:
            # 기간 없는 항목
            if ":" in clean:
                name, desc = clean.split(":", 1)
                activities.append({
                    "name": name.strip(),
                    "period": "",
                    "description": desc.strip(),
                })
            elif clean and len(clean) > 5:
                # 단독 항목
                time_match = re.search(r'(\d+)\s*시간', clean)
                if time_match:
                    activities.append({
                        "name": clean,
                        "period": "",
                        "description": "",
                    })

    if current:
        current["description"] = "\n".join(sub_items)
        activities.append(current)

    return activities




