import streamlit as st
from database import (
    init_db, get_profile, update_profile,
    get_experiences, add_experience, update_experience, delete_experience,
    get_practicals, add_practical, update_practical, delete_practical,
    get_projects, add_project, update_project, delete_project,
    get_skills, add_skill, delete_skill,
    get_certifications, add_certification, update_certification, delete_certification,
    get_activities, add_activity, update_activity, delete_activity,
    get_strengths, update_strengths,
    get_weaknesses, update_weaknesses,
    get_history, add_history, delete_history,
    get_full_portfolio, clear_all_portfolio, clear_section,
    init_users_db, register_user, verify_user, set_current_user, validate_username,
)
from prompt_builder import build_prompt
from portfolio_parser import parse_portfolio_text

# 사용자 계정 DB 초기화
init_users_db()


# ===========================
# 헬퍼 함수
# ===========================

def _save_parsed_portfolio(parsed, clear_existing=False):
    """파싱된 포트폴리오를 DB에 저장"""

    # 기존 데이터 초기화
    if clear_existing:
        for exp in get_experiences():
            delete_experience(exp["id"])
        for prac in get_practicals():
            delete_practical(prac["id"])
        for proj in get_projects():
            delete_project(proj["id"])
        for skill in get_skills():
            delete_skill(skill["id"])
        for cert in get_certifications():
            delete_certification(cert["id"])
        for act in get_activities():
            delete_activity(act["id"])
        update_strengths("")

    # 기본 정보 (항상 덮어쓰기)
    p = parsed["profile"]
    if any(p.values()):
        update_profile(p.get("name", ""), p.get("school", ""), p.get("major", ""), p.get("status", ""))

    # 경력
    for exp in parsed["experiences"]:
        add_experience(exp["company"], exp["period"], exp["role"], exp["description"])

    # 실습
    for prac in parsed["practicals"]:
        add_practical(prac["name"], prac["organization"], prac["period"], prac["description"])

    # 프로젝트
    for proj in parsed["projects"]:
        add_project(proj["name"], proj["period"], proj["tech_stack"], proj["role"], proj["description"])

    # 기술
    existing_skills = {s["skill"] for s in get_skills()}
    for skill in parsed["skills"]:
        if skill not in existing_skills:
            add_skill(skill)

    # 자격증
    for cert in parsed["certifications"]:
        add_certification(cert["name"], cert["date"])

    # 활동
    for act in parsed["activities"]:
        add_activity(act["name"], act["period"], act["description"])

    # 강점
    if parsed["strengths"]:
        existing = get_strengths()
        if existing and not clear_existing:
            update_strengths(existing + "\n\n" + parsed["strengths"])
        else:
            update_strengths(parsed["strengths"])

    # 단점
    if parsed.get("weaknesses"):
        existing = get_weaknesses()
        if existing and not clear_existing:
            update_weaknesses(existing + "\n\n" + parsed["weaknesses"])
        else:
            update_weaknesses(parsed["weaknesses"])

st.set_page_config(page_title="자소서 프롬프트 생성기", page_icon="📝", layout="wide")


# ===========================
# 로그인 / 회원가입
# ===========================

def show_login_page():
    """로그인 및 회원가입 UI"""
    st.title("📝 자소서 프롬프트 생성기")
    st.markdown("포트폴리오를 저장하고, 자소서 프롬프트를 자동 생성하세요.")
    st.caption("아이디는 2~30자, 한글/영문/숫자와 . _ - 만 사용할 수 있습니다.")
    st.divider()

    tab_login, tab_register = st.tabs(["🔑 로그인", "📋 회원가입"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("아이디", placeholder="아이디를 입력하세요")
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submitted = st.form_submit_button("로그인", use_container_width=True)
            if submitted:
                username = username.strip()
                if not username or not password:
                    st.error("아이디와 비밀번호를 입력해주세요.")
                elif verify_user(username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("아이디", placeholder="사용할 아이디 입력", key="reg_user")
            new_password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력", key="reg_pass")
            new_password2 = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호 다시 입력", key="reg_pass2")
            submitted = st.form_submit_button("회원가입", use_container_width=True)
            if submitted:
                new_username = new_username.strip()
                username_error = validate_username(new_username)
                if not new_username or not new_password:
                    st.error("아이디와 비밀번호를 입력해주세요.")
                elif username_error:
                    st.error(username_error)
                elif len(new_password) < 4:
                    st.error("비밀번호는 4자 이상이어야 합니다.")
                elif new_password != new_password2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif register_user(new_username, new_password):
                    st.success("회원가입 성공! 이제 로그인해주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")


# 로그인 체크
if not st.session_state.get("logged_in"):
    show_login_page()
    st.stop()

# 로그인 성공 → 사용자 DB 설정
set_current_user(st.session_state.username)
init_db()

# 사이드바 네비게이션
st.sidebar.markdown(f"👤 **{st.session_state.username}**님")
if st.sidebar.button("로그아웃"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.divider()
page = st.sidebar.radio(
    "메뉴",
    ["📥 포트폴리오 가져오기", "📋 포트폴리오", "✍️ 자소서 생성", "📂 히스토리"],
)


# ===========================
# 포트폴리오 가져오기 페이지
# ===========================
if page == "📥 포트폴리오 가져오기":
    st.title("포트폴리오 가져오기")
    st.markdown("""
    포트폴리오 텍스트를 통째로 붙여넣으면 **자동으로 섹션별로 분류**하여 저장합니다.

    Claude 대화에서 정리한 포트폴리오, 이력서 텍스트 등을 그대로 붙여넣으세요.
    """)

    raw_text = st.text_area(
        "포트폴리오 텍스트 붙여넣기",
        height=400,
        placeholder="여기에 포트폴리오 전체 텍스트를 붙여넣으세요...\n\n예시:\n기본 정보\n* 이름: 홍길동\n* 학교: OO대학교\n...",
    )

    if st.button("분석하기", type="primary", use_container_width=True):
        if not raw_text.strip():
            st.error("텍스트를 입력해주세요.")
        else:
            parsed = parse_portfolio_text(raw_text)
            st.session_state.parsed_portfolio = parsed
            st.session_state.import_confirmed = False

    # 파싱 결과 미리보기 & 확인
    if "parsed_portfolio" in st.session_state and not st.session_state.get("import_confirmed"):
        parsed = st.session_state.parsed_portfolio

        st.divider()
        st.subheader("분석 결과 미리보기")
        st.markdown("아래 내용을 확인하고, 맞으면 **저장하기**를 눌러주세요. 저장 후 '포트폴리오' 탭에서 수정할 수 있습니다.")

        # 기본 정보
        st.markdown("#### 기본 정보")
        p = parsed["profile"]
        if any(p.values()):
            for k, v in p.items():
                if v:
                    label = {"name": "이름", "school": "학교", "major": "전공", "status": "상태"}.get(k, k)
                    st.write(f"- **{label}**: {v}")
        else:
            st.caption("(감지된 기본 정보 없음)")

        # 경력/인턴
        if parsed["experiences"]:
            st.markdown(f"#### 경력/인턴 ({len(parsed['experiences'])}건)")
            for exp in parsed["experiences"]:
                st.write(f"- **{exp['company']}** ({exp['period']}) - {exp['role']}")

        # 실습/경험
        if parsed["practicals"]:
            st.markdown(f"#### 실습/경험 ({len(parsed['practicals'])}건)")
            for prac in parsed["practicals"]:
                org_text = f" @ {prac['organization']}" if prac['organization'] else ""
                st.write(f"- **{prac['name']}**{org_text} ({prac['period']})")

        # 프로젝트/연구
        if parsed["projects"]:
            st.markdown(f"#### 프로젝트/연구 ({len(parsed['projects'])}건)")
            for proj in parsed["projects"]:
                st.write(f"- **{proj['name']}** ({proj['period']})")

        # 기술 스택
        if parsed["skills"]:
            st.markdown(f"#### 기술 스택 ({len(parsed['skills'])}개)")
            st.write(", ".join(f"`{s}`" for s in parsed["skills"]))

        # 자격증/수상
        if parsed["certifications"]:
            st.markdown(f"#### 자격증/수상 ({len(parsed['certifications'])}건)")
            for cert in parsed["certifications"]:
                st.write(f"- **{cert['name']}** ({cert['date']})")

        # 활동/봉사
        if parsed["activities"]:
            st.markdown(f"#### 활동/봉사 ({len(parsed['activities'])}건)")
            for act in parsed["activities"]:
                period_text = f" ({act['period']})" if act['period'] else ""
                st.write(f"- **{act['name']}**{period_text}")

        # 성격/강점
        if parsed["strengths"]:
            st.markdown("#### 성격/강점/가치관")
            st.text(parsed["strengths"][:200] + "..." if len(parsed["strengths"]) > 200 else parsed["strengths"])

        st.divider()

        # 저장 옵션
        save_mode = st.radio(
            "저장 방식",
            ["기존 데이터에 추가 (병합)", "기존 데이터 초기화 후 새로 저장"],
            index=0,
        )

        if st.button("저장하기", type="primary", use_container_width=True):
            _save_parsed_portfolio(parsed, clear_existing=(save_mode == "기존 데이터 초기화 후 새로 저장"))
            st.session_state.import_confirmed = True
            st.success("포트폴리오가 저장되었습니다! '포트폴리오' 탭에서 확인하고 수정할 수 있습니다.")
            st.balloons()

    elif st.session_state.get("import_confirmed"):
        st.success("이미 저장 완료! '포트폴리오' 탭에서 내용을 확인/수정하세요.")
        if st.button("다시 가져오기"):
            st.session_state.pop("parsed_portfolio", None)
            st.session_state.pop("import_confirmed", None)
            st.rerun()


# ===========================
# 포트폴리오 페이지
# ===========================
elif page == "📋 포트폴리오":
    st.title("포트폴리오 관리")

    # --- 데이터 관리 ---
    with st.expander("🗑️ 데이터 삭제", expanded=False):
        st.caption("섹션별 삭제 또는 전체 초기화를 할 수 있습니다.")

        del_cols = st.columns(3)
        section_buttons = [
            ("기본 정보", "profile"),
            ("경력/인턴", "experiences"),
            ("실습/경험", "practicals"),
            ("프로젝트/연구", "projects"),
            ("기술 스택", "skills"),
            ("자격증/수상", "certifications"),
            ("활동/봉사", "activities"),
            ("성격/강점", "strengths"),
            ("단점/보완점", "weaknesses"),
        ]
        for i, (label, key) in enumerate(section_buttons):
            with del_cols[i % 3]:
                if st.button(f"{label} 삭제", key=f"clear_{key}", use_container_width=True):
                    clear_section(key)
                    st.success(f"'{label}' 섹션이 초기화되었습니다.")
                    st.rerun()

        st.divider()
        if st.button("⚠️ 포트폴리오 전체 삭제", type="secondary", use_container_width=True):
            st.session_state.confirm_clear_all = True

        if st.session_state.get("confirm_clear_all"):
            st.warning("정말 모든 포트폴리오 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("네, 전체 삭제합니다", type="primary"):
                    clear_all_portfolio()
                    st.session_state.confirm_clear_all = False
                    st.success("모든 포트폴리오 데이터가 삭제되었습니다.")
                    st.rerun()
            with col2:
                if st.button("취소"):
                    st.session_state.confirm_clear_all = False
                    st.rerun()

    # --- 기본 정보 ---
    st.header("기본 정보")
    profile = get_profile()
    with st.form("profile_form"):
        name = st.text_input("이름", value=profile.get("name", ""))
        school = st.text_input("학교", value=profile.get("school", ""))
        major = st.text_input("전공", value=profile.get("major", ""))
        status = st.text_input("상태 (재학/졸업 등)", value=profile.get("status", ""))
        if st.form_submit_button("기본 정보 저장"):
            update_profile(name, school, major, status)
            st.success("기본 정보가 저장되었습니다.")
            st.rerun()

    st.divider()

    # --- 경력/인턴 ---
    st.header("경력/인턴")
    experiences = get_experiences()
    for exp in experiences:
        with st.expander(f"{exp['company']} - {exp['role']}", expanded=False):
            with st.form(f"exp_{exp['id']}"):
                company = st.text_input("회사명", value=exp["company"], key=f"exp_company_{exp['id']}")
                period = st.text_input("기간", value=exp["period"], key=f"exp_period_{exp['id']}")
                role = st.text_input("역할", value=exp["role"], key=f"exp_role_{exp['id']}")
                description = st.text_area("내용", value=exp["description"], key=f"exp_desc_{exp['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("수정"):
                        update_experience(exp["id"], company, period, role, description)
                        st.success("수정되었습니다.")
                        st.rerun()
                with col2:
                    if st.form_submit_button("삭제", type="secondary"):
                        delete_experience(exp["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()

    with st.form("add_exp"):
        st.subheader("새 경력 추가")
        new_company = st.text_input("회사명", key="new_exp_company")
        new_period = st.text_input("기간 (예: 2024.01 - 2024.06)", key="new_exp_period")
        new_role = st.text_input("역할", key="new_exp_role")
        new_desc = st.text_area("내용", key="new_exp_desc")
        if st.form_submit_button("추가"):
            if new_company:
                add_experience(new_company, new_period, new_role, new_desc)
                st.success("경력이 추가되었습니다.")
                st.rerun()

    st.divider()

    # --- 실습/경험 ---
    st.header("실습/경험")
    practicals = get_practicals()
    for prac in practicals:
        with st.expander(f"{prac['name']} - {prac['organization']}", expanded=False):
            with st.form(f"prac_{prac['id']}"):
                pname = st.text_input("실습명", value=prac["name"], key=f"prac_name_{prac['id']}")
                org = st.text_input("기관", value=prac["organization"], key=f"prac_org_{prac['id']}")
                period = st.text_input("기간", value=prac["period"], key=f"prac_period_{prac['id']}")
                desc = st.text_area("내용", value=prac["description"], key=f"prac_desc_{prac['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("수정"):
                        update_practical(prac["id"], pname, org, period, desc)
                        st.success("수정되었습니다.")
                        st.rerun()
                with col2:
                    if st.form_submit_button("삭제", type="secondary"):
                        delete_practical(prac["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()

    with st.form("add_prac"):
        st.subheader("새 실습/경험 추가")
        new_pname = st.text_input("실습명", key="new_prac_name")
        new_org = st.text_input("기관", key="new_prac_org")
        new_period = st.text_input("기간", key="new_prac_period")
        new_desc = st.text_area("내용", key="new_prac_desc")
        if st.form_submit_button("추가"):
            if new_pname:
                add_practical(new_pname, new_org, new_period, new_desc)
                st.success("실습/경험이 추가되었습니다.")
                st.rerun()

    st.divider()

    # --- 프로젝트 ---
    st.header("프로젝트/연구")
    projects = get_projects()
    for proj in projects:
        with st.expander(f"{proj['name']}", expanded=False):
            with st.form(f"proj_{proj['id']}"):
                pname = st.text_input("프로젝트명", value=proj["name"], key=f"proj_name_{proj['id']}")
                period = st.text_input("기간", value=proj["period"], key=f"proj_period_{proj['id']}")
                tech = st.text_input("기술 스택", value=proj["tech_stack"], key=f"proj_tech_{proj['id']}")
                role = st.text_input("역할", value=proj["role"], key=f"proj_role_{proj['id']}")
                desc = st.text_area("내용", value=proj["description"], key=f"proj_desc_{proj['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("수정"):
                        update_project(proj["id"], pname, period, tech, role, desc)
                        st.success("수정되었습니다.")
                        st.rerun()
                with col2:
                    if st.form_submit_button("삭제", type="secondary"):
                        delete_project(proj["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()

    with st.form("add_proj"):
        st.subheader("새 프로젝트 추가")
        new_pname = st.text_input("프로젝트명", key="new_proj_name")
        new_period = st.text_input("기간", key="new_proj_period")
        new_tech = st.text_input("기술 스택 (쉼표로 구분)", key="new_proj_tech")
        new_role = st.text_input("역할", key="new_proj_role")
        new_desc = st.text_area("내용", key="new_proj_desc")
        if st.form_submit_button("추가"):
            if new_pname:
                add_project(new_pname, new_period, new_tech, new_role, new_desc)
                st.success("프로젝트가 추가되었습니다.")
                st.rerun()

    st.divider()

    # --- 기술 스택 ---
    st.header("기술 스택")
    skills = get_skills()
    if skills:
        cols = st.columns(4)
        for i, skill in enumerate(skills):
            with cols[i % 4]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"`{skill['skill']}`")
                with col2:
                    if st.button("X", key=f"del_skill_{skill['id']}"):
                        delete_skill(skill["id"])
                        st.rerun()

    with st.form("add_skill"):
        new_skill = st.text_input("기술 추가 (예: Python, React, AWS 등)")
        if st.form_submit_button("추가"):
            if new_skill:
                add_skill(new_skill)
                st.success(f"'{new_skill}' 추가됨")
                st.rerun()

    st.divider()

    # --- 자격증/수상 ---
    st.header("자격증/수상")
    certs = get_certifications()
    for cert in certs:
        with st.expander(f"{cert['name']} ({cert['date']})", expanded=False):
            with st.form(f"cert_{cert['id']}"):
                cname = st.text_input("자격증/수상명", value=cert["name"], key=f"cert_name_{cert['id']}")
                cdate = st.text_input("취득일/수상일", value=cert["date"], key=f"cert_date_{cert['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("수정"):
                        update_certification(cert["id"], cname, cdate)
                        st.success("수정되었습니다.")
                        st.rerun()
                with col2:
                    if st.form_submit_button("삭제", type="secondary"):
                        delete_certification(cert["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()

    with st.form("add_cert"):
        st.subheader("새 자격증/수상 추가")
        new_cname = st.text_input("자격증/수상명", key="new_cert_name")
        new_cdate = st.text_input("취득일/수상일", key="new_cert_date")
        if st.form_submit_button("추가"):
            if new_cname:
                add_certification(new_cname, new_cdate)
                st.success("자격증/수상이 추가되었습니다.")
                st.rerun()

    st.divider()

    # --- 활동/봉사 ---
    st.header("활동/봉사")
    activities = get_activities()
    for act in activities:
        with st.expander(f"{act['name']} ({act['period']})", expanded=False):
            with st.form(f"act_{act['id']}"):
                aname = st.text_input("활동명", value=act["name"], key=f"act_name_{act['id']}")
                aperiod = st.text_input("기간", value=act["period"], key=f"act_period_{act['id']}")
                adesc = st.text_area("내용", value=act["description"], key=f"act_desc_{act['id']}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("수정"):
                        update_activity(act["id"], aname, aperiod, adesc)
                        st.success("수정되었습니다.")
                        st.rerun()
                with col2:
                    if st.form_submit_button("삭제", type="secondary"):
                        delete_activity(act["id"])
                        st.success("삭제되었습니다.")
                        st.rerun()

    with st.form("add_act"):
        st.subheader("새 활동/봉사 추가")
        new_aname = st.text_input("활동명", key="new_act_name")
        new_aperiod = st.text_input("기간", key="new_act_period")
        new_adesc = st.text_area("내용", key="new_act_desc")
        if st.form_submit_button("추가"):
            if new_aname:
                add_activity(new_aname, new_aperiod, new_adesc)
                st.success("활동/봉사가 추가되었습니다.")
                st.rerun()

    st.divider()

    # --- 성격/강점 ---
    st.header("성격/강점/가치관")
    strengths = get_strengths()
    with st.form("strengths_form"):
        content = st.text_area(
            "자유롭게 작성하세요 (성격, 강점, 가치관, 특기 등)",
            value=strengths,
            height=200,
        )
        if st.form_submit_button("저장"):
            update_strengths(content)
            st.success("저장되었습니다.")
            st.rerun()

    st.divider()

    # --- 단점/보완점 ---
    st.header("단점/보완점")
    weaknesses = get_weaknesses()
    with st.form("weaknesses_form"):
        w_content = st.text_area(
            "자유롭게 작성하세요 (단점, 보완점, 극복 노력 등)",
            value=weaknesses,
            height=200,
            placeholder="예: 꼼꼼한 성격 때문에 업무 속도가 느릴 때가 있지만, 체크리스트를 활용하여 우선순위를 정하는 방식으로 개선하고 있습니다.",
        )
        if st.form_submit_button("저장"):
            update_weaknesses(w_content)
            st.success("저장되었습니다.")
            st.rerun()


# ===========================
# 자소서 생성 페이지
# ===========================
elif page == "✍️ 자소서 생성":
    st.title("자소서 프롬프트 생성")

    # 포트폴리오 확인
    portfolio = get_full_portfolio()
    if not portfolio["profile"].get("name"):
        st.warning("먼저 '포트폴리오 가져오기' 또는 '포트폴리오' 탭에서 정보를 입력해주세요.")

    # 회사/직무 입력
    col1, col2 = st.columns(2)
    with col1:
        company = st.text_input("지원 회사")
    with col2:
        position = st.text_input("지원 직무")

    st.divider()

    # 질문 항목 동적 관리
    st.subheader("자소서 질문 항목")

    if "questions" not in st.session_state:
        st.session_state.questions = [{"question": "", "char_limit": 500}]

    # 질문 추가/삭제 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("질문 추가"):
            st.session_state.questions.append({"question": "", "char_limit": 500})
            st.rerun()
    with col2:
        if len(st.session_state.questions) > 1:
            if st.button("마지막 질문 삭제"):
                st.session_state.questions.pop()
                st.rerun()

    # 질문 입력 폼
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"**질문 {i + 1}**")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.session_state.questions[i]["question"] = st.text_area(
                f"질문 내용",
                value=q["question"],
                key=f"q_{i}",
                label_visibility="collapsed",
                placeholder="예: 지원동기를 작성해주세요.",
            )
        with col2:
            st.session_state.questions[i]["char_limit"] = st.number_input(
                f"글자수",
                min_value=50,
                max_value=5000,
                value=q["char_limit"],
                step=50,
                key=f"cl_{i}",
                label_visibility="collapsed",
            )
            st.caption("글자수 제한")

    st.divider()

    # 프롬프트 생성
    if st.button("프롬프트 생성", type="primary", use_container_width=True):
        if not company or not position:
            st.error("회사명과 직무를 입력해주세요.")
        elif not any(q["question"] for q in st.session_state.questions):
            st.error("최소 하나의 질문을 입력해주세요.")
        else:
            valid_questions = [q for q in st.session_state.questions if q["question"]]
            prompt = build_prompt(portfolio, company, position, valid_questions)

            # 히스토리 저장
            add_history(company, position, prompt)

            st.success("프롬프트가 생성되었습니다! 아래 내용을 복사하여 Claude/ChatGPT에 붙여넣으세요.")

            # 프롬프트 표시
            st.code(prompt, language=None)

            st.info("💡 위 텍스트 박스 우측 상단의 복사 버튼을 클릭하여 복사하세요.")


# ===========================
# 히스토리 페이지
# ===========================
elif page == "📂 히스토리":
    st.title("생성 히스토리")

    history = get_history()

    if not history:
        st.info("아직 생성한 프롬프트가 없습니다.")
    else:
        for item in history:
            with st.expander(f"{item['company']} - {item['position']} ({item['created_at'][:16]})"):
                st.code(item["prompt"], language=None)
                if st.button("삭제", key=f"del_hist_{item['id']}"):
                    delete_history(item["id"])
                    st.success("삭제되었습니다.")
                    st.rerun()


