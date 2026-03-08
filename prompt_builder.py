def format_portfolio(portfolio):
    """포트폴리오 딕셔너리를 구조화된 텍스트로 변환"""
    sections = []

    # 기본 정보
    p = portfolio["profile"]
    if any([p.get("name"), p.get("school"), p.get("major")]):
        lines = ["## 기본 정보"]
        if p.get("name"):
            lines.append(f"- 이름: {p['name']}")
        if p.get("school"):
            lines.append(f"- 학교: {p['school']}")
        if p.get("major"):
            lines.append(f"- 전공: {p['major']}")
        if p.get("status"):
            lines.append(f"- 상태: {p['status']}")
        sections.append("\n".join(lines))

    # 경력/인턴
    if portfolio["experiences"]:
        lines = ["## 경력/인턴 경험"]
        for exp in portfolio["experiences"]:
            lines.append(f"### {exp['company']} ({exp['period']})")
            lines.append(f"- 역할: {exp['role']}")
            lines.append(f"- 내용: {exp['description']}")
        sections.append("\n".join(lines))

    # 실습/경험
    if portfolio["practicals"]:
        lines = ["## 실습/경험"]
        for prac in portfolio["practicals"]:
            lines.append(f"### {prac['name']} - {prac['organization']} ({prac['period']})")
            lines.append(f"- 내용: {prac['description']}")
        sections.append("\n".join(lines))

    # 프로젝트
    if portfolio["projects"]:
        lines = ["## 프로젝트"]
        for proj in portfolio["projects"]:
            lines.append(f"### {proj['name']} ({proj['period']})")
            if proj.get("tech_stack"):
                lines.append(f"- 기술 스택: {proj['tech_stack']}")
            lines.append(f"- 역할: {proj['role']}")
            lines.append(f"- 내용: {proj['description']}")
        sections.append("\n".join(lines))

    # 기술 스택
    if portfolio["skills"]:
        skill_list = ", ".join(s["skill"] for s in portfolio["skills"])
        sections.append(f"## 기술 스택\n{skill_list}")

    # 자격증/수상
    if portfolio["certifications"]:
        lines = ["## 자격증/수상"]
        for cert in portfolio["certifications"]:
            lines.append(f"- {cert['name']} ({cert['date']})")
        sections.append("\n".join(lines))

    # 활동/봉사
    if portfolio["activities"]:
        lines = ["## 활동/봉사"]
        for act in portfolio["activities"]:
            lines.append(f"### {act['name']} ({act['period']})")
            lines.append(f"- 내용: {act['description']}")
        sections.append("\n".join(lines))

    # 성격/강점
    if portfolio["strengths"]:
        sections.append(f"## 성격/강점/가치관\n{portfolio['strengths']}")

    # 단점/보완점
    if portfolio.get("weaknesses"):
        sections.append(f"## 단점/보완점\n{portfolio['weaknesses']}")

    return "\n\n".join(sections)


def build_prompt(portfolio, company, position, questions):
    """포트폴리오 + 자소서 양식으로 최적화된 프롬프트 생성"""
    portfolio_text = format_portfolio(portfolio)

    # 질문 목록 구성
    questions_text = ""
    for i, q in enumerate(questions, 1):
        questions_text += f"\n### 질문 {i}\n"
        questions_text += f"질문: {q['question']}\n"
        questions_text += f"글자수 제한: {q['char_limit']}자 이내\n"

    prompt = f"""당신은 한국어 자기소개서 작성 전문가입니다. 아래 지원자의 포트폴리오를 바탕으로 자기소개서를 작성해주세요.

---

# 지원자 포트폴리오

{portfolio_text}

---

# 자소서 양식

- 지원 회사: {company}
- 지원 직무: {position}
{questions_text}

---

# 작성 지침

1. 각 질문에 대해 **글자수 제한을 반드시 준수**하세요. (공백 포함)
2. 포트폴리오의 **구체적인 경험과 사례**를 활용하여 작성하세요.
3. STAR 기법(상황-과제-행동-결과)을 활용하되, 자연스러운 문체로 작성하세요.
4. 추상적인 표현보다 **구체적인 숫자, 성과, 행동**을 포함하세요.
5. 각 답변은 해당 회사/직무에 맞게 **맞춤형으로** 작성하세요.
6. 진정성 있고 차별화된 내용으로 작성하세요.
7. 각 답변의 마지막에 (현재 글자수: N자)를 표시해주세요.

각 질문에 대한 답변을 작성해주세요."""

    return prompt
