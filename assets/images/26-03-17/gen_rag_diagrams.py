"""
RAG Study Post - Diagram PNG Generator
Light theme matching SVG source designs
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager
import os

# Korean font setup
for fname in font_manager.findSystemFonts():
    if 'malgun' in fname.lower() or 'Malgun' in fname:
        font_manager.fontManager.addfont(fname)
        break
plt.rcParams['font.family'] = ['Malgun Gothic', 'NanumGothic', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

OUT = os.path.dirname(os.path.abspath(__file__))

# Color palette (light theme)
C = {
    'gray_fill':   '#F1EFE8', 'gray_stroke':  '#5F5E5A', 'gray_text':   '#2C2C2A',
    'purple_fill': '#EEEDFE', 'purple_stroke':'#534AB7', 'purple_text': '#26215C',
    'green_fill':  '#E1F5EE', 'green_stroke': '#0F6E56', 'green_text':  '#085041',
    'blue_fill':   '#E6F1FB', 'blue_stroke':  '#185FA5', 'blue_text':   '#0C447C',
    'orange_fill': '#FAEEDA', 'orange_stroke':'#BA7517', 'orange_text': '#412402',
    'red_fill':    '#FAECE7', 'red_stroke':   '#993C1D', 'red_text':    '#712B13',
    'olive_fill':  '#EAF3DE', 'olive_stroke': '#3B6D11', 'olive_text':  '#173404',
    'bg': '#FFFFFF', 'line': '#888780', 'label': '#5F5E5A',
}

def box(ax, x, y, w, h, fill, stroke, text1, text2='', text1_size=10, text2_size=9, text1_color=None, text2_color=None, radius=0.4):
    tc1 = text1_color or C['gray_text']
    tc2 = text2_color or C['label']
    rect = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                          facecolor=fill, edgecolor=stroke, linewidth=0.8, zorder=2)
    ax.add_patch(rect)
    cy = y + h/2
    if text2:
        ax.text(x + w/2, cy + h*0.14, text1, ha='center', va='center',
                fontsize=text1_size, fontweight='bold', color=tc1, zorder=3)
        ax.text(x + w/2, cy - h*0.18, text2, ha='center', va='center',
                fontsize=text2_size, color=tc2, zorder=3)
    else:
        ax.text(x + w/2, cy, text1, ha='center', va='center',
                fontsize=text1_size, fontweight='bold', color=tc1, zorder=3)

def arrow(ax, x1, y1, x2, y2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.2),
                zorder=3)

def line_h(ax, x1, x2, y, color=None):
    ax.plot([x1, x2], [y, y], '-', color=color or C['line'], lw=1.0, zorder=2)

def line_v(ax, x, y1, y2, color=None):
    ax.plot([x, x], [y1, y2], '-', color=color or C['line'], lw=1.0, zorder=2)

# ─────────────────────────────────────────────
# Diagram 01: AI 에이전트 전체 구조
# ─────────────────────────────────────────────
def make_diagram_01():
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 8); ax.set_ylim(0, 6)
    ax.axis('off')

    # 사용자 입력 (top center)
    box(ax, 2.7, 5.15, 2.6, 0.6, C['gray_fill'], C['gray_stroke'],
        '사용자 입력', '', text1_color=C['gray_text'])
    arrow(ax, 4.0, 5.15, 4.0, 4.7)

    # 미들웨어 레이어 (wide orange)
    box(ax, 0.8, 4.05, 6.4, 0.65, C['orange_fill'], C['orange_stroke'],
        '미들웨어 레이어',
        'before_agent · before_model · wrap_model_call · after_model',
        text1_size=10, text2_size=8,
        text1_color=C['orange_text'], text2_color='#633806')
    arrow(ax, 4.0, 4.05, 4.0, 3.55)

    # LLM 뇌 (center purple)
    box(ax, 2.7, 2.7, 2.6, 0.8, C['purple_fill'], C['purple_stroke'],
        'LLM 뇌', '추론 · 판단 · ReAct 패턴',
        text1_color=C['purple_text'], text2_color=C['purple_stroke'])

    # 툴 (left green)
    box(ax, 0.3, 2.7, 1.8, 0.8, C['green_fill'], C['green_stroke'],
        '툴 (핸들러)', '@tool 데코레이터',
        text1_color=C['green_text'], text2_color=C['green_stroke'])
    # arrows LLM ↔ tool
    ax.annotate('', xy=(2.1, 3.1), xytext=(2.7, 3.1),
                arrowprops=dict(arrowstyle='<->', color=C['green_stroke'], lw=1.2), zorder=3)

    # RAG 검색 툴 (right green)
    box(ax, 5.9, 2.7, 1.8, 0.8, C['green_fill'], C['green_stroke'],
        'RAG 검색 툴', '벡터 DB 연결',
        text1_color=C['green_text'], text2_color=C['green_stroke'])
    ax.annotate('', xy=(5.9, 3.1), xytext=(5.3, 3.1),
                arrowprops=dict(arrowstyle='<->', color=C['green_stroke'], lw=1.2), zorder=3)

    arrow(ax, 4.0, 2.7, 4.0, 2.2)

    # 단기 메모리 (left blue)
    box(ax, 0.8, 1.3, 2.8, 0.8, C['blue_fill'], C['blue_stroke'],
        '단기 메모리', 'InMemorySaver · thread_id',
        text1_color=C['blue_text'], text2_color=C['blue_stroke'])
    # 장기 메모리 (right green)
    box(ax, 4.4, 1.3, 2.8, 0.8, C['green_fill'], C['green_stroke'],
        '장기 메모리', 'InMemoryStore · namespace',
        text1_color=C['green_text'], text2_color=C['green_stroke'])

    # converge arrows
    ax.annotate('', xy=(2.95, 1.3), xytext=(3.6, 2.2),
                arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.0), zorder=3)
    ax.annotate('', xy=(5.05, 1.3), xytext=(4.4, 2.2),
                arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.0), zorder=3)

    # merge to final
    ax.annotate('', xy=(4.0, 0.9), xytext=(3.2, 1.3),
                arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.0), zorder=3)
    ax.annotate('', xy=(4.0, 0.9), xytext=(4.8, 1.3),
                arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.0), zorder=3)

    # 최종 답변
    box(ax, 2.7, 0.25, 2.6, 0.6, C['gray_fill'], C['gray_stroke'],
        '최종 답변 → 사용자', '', text1_color=C['gray_text'])

    # labels
    ax.text(1.4, 2.55, '현재 세션', ha='center', va='top', fontsize=8, color=C['label'])
    ax.text(5.8, 2.55, '세션 이후', ha='center', va='top', fontsize=8, color=C['label'])

    plt.tight_layout(pad=0.3)
    plt.savefig(os.path.join(OUT, 'diagram_01_agent_structure.png'), dpi=150, bbox_inches='tight',
                facecolor=C['bg'])
    plt.close()
    print("diagram_01 saved")


# ─────────────────────────────────────────────
# Diagram 02: 에이전트 메시지 흐름
# ─────────────────────────────────────────────
def make_diagram_02():
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 8); ax.set_ylim(0, 7)
    ax.axis('off')

    # step 1: HumanMessage
    box(ax, 0.4, 5.9, 7.2, 0.85, C['blue_fill'], C['blue_stroke'],
        'HumanMessage', '서울 날씨 어때요?',
        text1_color=C['blue_text'], text2_color='#0C447C', text1_size=9, text2_size=10)
    ax.text(0.6, 6.55, '①', fontsize=9, color=C['blue_stroke'])
    arrow(ax, 4.0, 5.9, 4.0, 5.55)

    # step 2: AIMessage (tool call)
    box(ax, 0.4, 4.4, 7.2, 1.1, C['purple_fill'], C['purple_stroke'],
        'AIMessage  ← LLM이 스스로 생성',
        'content: ""  (비어 있음)\ntool_calls: [ { name: "get_weather",  args: { location: "서울" } } ]',
        text1_color=C['purple_stroke'], text2_color=C['purple_text'], text1_size=9, text2_size=9)
    ax.text(0.6, 5.35, '②', fontsize=9, color=C['purple_stroke'])
    # ReAct badge
    badge = FancyBboxPatch((5.5, 4.5), 1.9, 0.38, boxstyle="round,pad=0,rounding_size=0.2",
                           facecolor=C['orange_fill'], edgecolor=C['orange_stroke'], lw=0.6, zorder=4)
    ax.add_patch(badge)
    ax.text(6.45, 4.69, 'ReAct: 추론 → 행동', ha='center', va='center', fontsize=8,
            color=C['orange_text'], zorder=5)
    ax.text(4.1, 4.15, 'LangChain 자동 실행', ha='left', fontsize=8, color=C['label'])
    arrow(ax, 4.0, 4.4, 4.0, 4.05)

    # step 3: ToolMessage
    box(ax, 0.4, 3.0, 7.2, 0.95, C['green_fill'], C['green_stroke'],
        'ToolMessage  ← 함수 실행 결과',
        '서울의 날씨는 맑고 영하 2도입니다',
        text1_color=C['green_stroke'], text2_color=C['green_text'], text1_size=9, text2_size=10)
    ax.text(0.6, 3.8, '③', fontsize=9, color=C['green_stroke'])
    arrow(ax, 4.0, 3.0, 4.0, 2.65)

    # step 4: AIMessage (final)
    box(ax, 0.4, 1.65, 7.2, 1.1, C['purple_fill'], C['purple_stroke'],
        'AIMessage  ← 최종 답변 생성',
        '서울은 오늘 맑고 영하 2도에요. 보온에 신경 쓰세요!',
        text1_color=C['purple_stroke'], text2_color=C['purple_text'], text1_size=9, text2_size=10)
    ax.text(0.6, 2.6, '④', fontsize=9, color=C['purple_stroke'])
    arrow(ax, 4.0, 1.65, 4.0, 1.3)

    # final result box
    box(ax, 2.0, 0.35, 4.0, 0.85, C['gray_fill'], C['gray_stroke'],
        'result["messages"][-1].content', '',
        text1_color=C['gray_text'], text1_size=10)

    plt.tight_layout(pad=0.3)
    plt.savefig(os.path.join(OUT, 'diagram_02_message_flow.png'), dpi=150, bbox_inches='tight',
                facecolor=C['bg'])
    plt.close()
    print("diagram_02 saved")


# ─────────────────────────────────────────────
# Diagram 03: 미들웨어 레이어 구조
# ─────────────────────────────────────────────
def make_diagram_03():
    fig, ax = plt.subplots(figsize=(8, 6.5))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 8); ax.set_ylim(0, 6.5)
    ax.axis('off')

    # Outermost: @before_agent / @after_agent (orange)
    outer = FancyBboxPatch((0.3, 0.4), 7.4, 5.7, boxstyle="round,pad=0,rounding_size=0.5",
                           facecolor=C['orange_fill'], edgecolor=C['orange_stroke'], lw=1.0, zorder=1)
    ax.add_patch(outer)
    ax.text(0.6, 5.88, '@before_agent', fontsize=10, fontweight='bold', color=C['orange_stroke'], zorder=4)
    ax.text(7.7, 5.88, '단 1번 실행 · 입장 검문', ha='right', fontsize=9, color=C['orange_stroke'], zorder=4)
    ax.text(0.6, 0.6, '@after_agent', fontsize=10, fontweight='bold', color=C['orange_stroke'], zorder=4)
    ax.text(7.7, 0.6, '단 1번 실행 · 품질 가드레일', ha='right', fontsize=9, color=C['orange_stroke'], zorder=4)

    # Middle: @before_model / @after_model (red)
    middle = FancyBboxPatch((0.8, 0.9), 6.4, 4.7, boxstyle="round,pad=0,rounding_size=0.5",
                            facecolor=C['red_fill'], edgecolor=C['red_stroke'], lw=1.0, zorder=2)
    ax.add_patch(middle)
    ax.text(1.1, 5.42, '@before_model', fontsize=10, fontweight='bold', color=C['red_stroke'], zorder=4)
    ax.text(7.2, 5.42, '모델 호출마다 · 여러 번', ha='right', fontsize=9, color=C['red_stroke'], zorder=4)
    ax.text(1.1, 1.1, '@after_model', fontsize=10, fontweight='bold', color=C['red_stroke'], zorder=4)
    ax.text(7.2, 1.1, '모델 호출마다 · 여러 번', ha='right', fontsize=9, color=C['red_stroke'], zorder=4)

    # Inner: @wrap_model_call (gray)
    inner = FancyBboxPatch((1.3, 1.5), 5.4, 3.7, boxstyle="round,pad=0,rounding_size=0.4",
                           facecolor=C['gray_fill'], edgecolor=C['gray_stroke'], lw=0.8, zorder=3)
    ax.add_patch(inner)
    ax.text(1.6, 4.98, '@wrap_model_call', fontsize=10, fontweight='bold', color=C['gray_stroke'], zorder=4)
    ax.text(6.7, 4.98, 'request 수정 가능', ha='right', fontsize=9, color=C['gray_stroke'], zorder=4)

    # Center: LLM 모델 호출 (purple)
    center = FancyBboxPatch((2.3, 2.2), 3.4, 1.5, boxstyle="round,pad=0,rounding_size=0.4",
                            facecolor=C['purple_fill'], edgecolor=C['purple_stroke'], lw=1.5, zorder=4)
    ax.add_patch(center)
    ax.text(4.0, 3.12, 'LLM 모델 호출', ha='center', va='center',
            fontsize=12, fontweight='bold', color=C['purple_text'], zorder=5)
    ax.text(4.0, 2.6, 'gpt-5 · claude · gemini', ha='center', va='center',
            fontsize=9, color=C['purple_stroke'], zorder=5)

    # Side labels
    # Bronze style (읽기만)
    badge1 = FancyBboxPatch((5.8, 3.25), 0.85, 0.35, boxstyle="round,pad=0,rounding_size=0.15",
                            facecolor=C['green_fill'], edgecolor=C['green_stroke'], lw=0.5, zorder=5)
    ax.add_patch(badge1)
    ax.text(6.225, 3.425, '브론즈 스타일', ha='center', va='center', fontsize=8,
            color=C['green_text'], zorder=6)
    ax.text(6.225, 2.95, '읽기만 가능', ha='center', fontsize=8, color=C['label'], zorder=6)

    # Meng style (수정 가능)
    badge2 = FancyBboxPatch((5.8, 2.3), 0.85, 0.35, boxstyle="round,pad=0,rounding_size=0.15",
                            facecolor=C['red_fill'], edgecolor=C['red_stroke'], lw=0.5, zorder=5)
    ax.add_patch(badge2)
    ax.text(6.225, 2.475, '멩 스타일', ha='center', va='center', fontsize=8,
            color=C['red_text'], zorder=6)
    ax.text(6.225, 2.0, '수정 가능', ha='center', fontsize=8, color=C['label'], zorder=6)

    plt.tight_layout(pad=0.3)
    plt.savefig(os.path.join(OUT, 'diagram_03_middleware_layers.png'), dpi=150, bbox_inches='tight',
                facecolor=C['bg'])
    plt.close()
    print("diagram_03 saved")


# ─────────────────────────────────────────────
# Diagram 04: RAG 파이프라인
# ─────────────────────────────────────────────
def make_diagram_04():
    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 9); ax.set_ylim(0, 6)
    ax.axis('off')

    # Phase 1 title
    ax.text(4.5, 5.8, 'Phase 1 — 인덱싱 (한 번만 실행)', ha='center', fontsize=10, color=C['label'])

    # Phase 1 background
    p1bg = FancyBboxPatch((0.2, 4.5), 8.6, 1.15, boxstyle="round,pad=0,rounding_size=0.3",
                          facecolor='#F8F7F3', edgecolor='#C8C6BC', lw=0.6, zorder=1)
    ax.add_patch(p1bg)

    # Phase 1 steps
    steps1 = [
        ('원본 파일', 'PDF · CSV · DB', C['gray_fill'], C['gray_stroke']),
        ('① Load', 'Document 객체', C['green_fill'], C['green_stroke']),
        ('② Split', '300~500자 청크', C['green_fill'], C['green_stroke']),
        ('③ Embed', '벡터 변환', C['blue_fill'], C['blue_stroke']),
        ('④ Store', 'Chroma DB', C['purple_fill'], C['purple_stroke']),
    ]
    xs1 = [0.4, 2.15, 3.9, 5.65, 7.4]
    for i, ((t1, t2, f, s), x) in enumerate(zip(steps1, xs1)):
        box(ax, x, 4.6, 1.5, 0.95, f, s, t1, t2,
            text1_size=10, text2_size=8,
            text1_color=s.replace('A5','47').replace('E5','0C'),
            text2_color=s)
        if i < len(steps1) - 1:
            ax.annotate('', xy=(xs1[i+1], 5.075), xytext=(x + 1.5, 5.075),
                        arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.2), zorder=3)

    # Phase 2 title
    ax.text(4.5, 3.85, 'Phase 2 — 검색 + 생성 (질문마다 실행)', ha='center', fontsize=10, color=C['label'])

    # Phase 2 background
    p2bg = FancyBboxPatch((0.2, 2.55), 8.6, 1.15, boxstyle="round,pad=0,rounding_size=0.3",
                          facecolor='#F8F7F3', edgecolor='#C8C6BC', lw=0.6, zorder=1)
    ax.add_patch(p2bg)

    steps2 = [
        ('사용자 질문', '"피자라 뭐야?"', C['gray_fill'], C['gray_stroke']),
        ('질문 임베딩', '벡터 변환', C['blue_fill'], C['blue_stroke']),
        ('유사도 검색', 'Top-K · MMR', C['purple_fill'], C['purple_stroke']),
        ('LLM 생성', '참고 + 질문', C['purple_fill'], C['purple_stroke']),
        ('최종 답변', '', C['green_fill'], C['green_stroke']),
    ]
    xs2 = [0.4, 2.15, 3.9, 5.65, 7.4]
    for i, ((t1, t2, f, s), x) in enumerate(zip(steps2, xs2)):
        box(ax, x, 2.65, 1.5, 0.95, f, s, t1, t2,
            text1_size=10, text2_size=8,
            text1_color=s.replace('A5','47').replace('E5','0C'),
            text2_color=s)
        if i < len(steps2) - 1:
            ax.annotate('', xy=(xs2[i+1], 3.125), xytext=(x + 1.5, 3.125),
                        arrowprops=dict(arrowstyle='->', color=C['line'], lw=1.2), zorder=3)

    # DB query arrow (Phase1 Store → Phase2 검색)
    ax.annotate('', xy=(4.75, 3.6), xytext=(8.15, 4.6),
                arrowprops=dict(arrowstyle='->', color='#7F77DD', lw=1.0,
                                linestyle='dashed'), zorder=3)
    ax.text(7.0, 4.25, 'DB 조회', fontsize=9, color='#7F77DD')

    # Bottom note
    note = FancyBboxPatch((0.8, 0.3), 7.4, 0.55, boxstyle="round,pad=0,rounding_size=0.3",
                          facecolor=C['orange_fill'], edgecolor=C['orange_stroke'], lw=0.6, zorder=2)
    ax.add_patch(note)
    ax.text(4.5, 0.575, 'CacheBackedEmbeddings: 동일 텍스트 재임베딩 시 API 비용 $0',
            ha='center', va='center', fontsize=9, color=C['orange_text'], zorder=3)

    plt.tight_layout(pad=0.3)
    plt.savefig(os.path.join(OUT, 'diagram_04_rag_pipeline.png'), dpi=150, bbox_inches='tight',
                facecolor=C['bg'])
    plt.close()
    print("diagram_04 saved")


# ─────────────────────────────────────────────
# Diagram 05: 메모리 시스템 + 가드레일
# ─────────────────────────────────────────────
def make_diagram_05():
    fig, ax = plt.subplots(figsize=(9, 6.5))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 9); ax.set_ylim(0, 6.5)
    ax.axis('off')

    # Section titles
    ax.text(2.3, 6.2, '메모리 시스템', ha='center', fontsize=11, fontweight='bold', color=C['gray_text'])
    ax.text(6.7, 6.2, '가드레일', ha='center', fontsize=11, fontweight='bold', color=C['gray_text'])

    # Divider
    ax.plot([4.5, 4.5], [0.5, 6.3], '--', color='#D0CEC6', lw=1.5)

    # ── LEFT: Memory ──

    # 단기 메모리 (blue)
    bg1 = FancyBboxPatch((0.2, 3.6), 4.1, 2.4, boxstyle="round,pad=0,rounding_size=0.4",
                         facecolor=C['blue_fill'], edgecolor=C['blue_stroke'], lw=0.8, zorder=1)
    ax.add_patch(bg1)
    ax.text(2.25, 5.82, '단기 메모리', ha='center', fontsize=11, fontweight='bold',
            color=C['blue_text'], zorder=3)
    ax.text(2.25, 5.52, 'InMemorySaver + checkpointer', ha='center', fontsize=9,
            color=C['blue_stroke'], zorder=3)

    box(ax, 0.4, 4.45, 3.7, 0.5, '#B5D4F4', C['blue_stroke'],
        'thread_id: "A" → 세션 A 기억', '', text1_size=9, text1_color='#042C53')
    box(ax, 0.4, 3.85, 3.7, 0.5, '#B5D4F4', C['blue_stroke'],
        'thread_id: "B" → 완전히 다른 세션', '', text1_size=9, text1_color='#042C53')

    arrow(ax, 2.25, 3.6, 2.25, 3.25)

    # 장기 메모리 (green)
    bg2 = FancyBboxPatch((0.2, 0.8), 4.1, 2.35, boxstyle="round,pad=0,rounding_size=0.4",
                         facecolor=C['green_fill'], edgecolor=C['green_stroke'], lw=0.8, zorder=1)
    ax.add_patch(bg2)
    ax.text(2.25, 2.93, '장기 메모리', ha='center', fontsize=11, fontweight='bold',
            color=C['green_text'], zorder=3)
    ax.text(2.25, 2.63, 'InMemoryStore · 세션 이후 영구 기억', ha='center', fontsize=9,
            color=C['green_stroke'], zorder=3)

    box(ax, 0.4, 2.2, 3.7, 0.35, '#9FE1CB', C['green_stroke'],
        'namespace: ("user_123", "app")', '', text1_size=9, text1_color='#04342C')
    box(ax, 0.4, 1.75, 3.7, 0.35, '#9FE1CB', C['green_stroke'],
        'store.put / store.get / store.search', '', text1_size=9, text1_color='#04342C')
    box(ax, 0.4, 1.3, 3.7, 0.35, '#9FE1CB', C['green_stroke'],
        '@tool로 AI가 스스로 저장/조회', '', text1_size=9, text1_color='#04342C')

    # ── RIGHT: Guardrails ──

    # 결정론적 가드레일 (green)
    bg3 = FancyBboxPatch((4.7, 3.6), 4.1, 2.4, boxstyle="round,pad=0,rounding_size=0.4",
                         facecolor=C['green_fill'], edgecolor=C['green_stroke'], lw=0.8, zorder=1)
    ax.add_patch(bg3)
    ax.text(6.75, 5.82, '결정론적 가드레일', ha='center', fontsize=11, fontweight='bold',
            color=C['green_text'], zorder=3)
    ax.text(6.75, 5.52, '@before_agent(can_jump_to="end")', ha='center', fontsize=9,
            color=C['green_stroke'], zorder=3)

    box(ax, 4.9, 4.45, 3.7, 0.5, '#9FE1CB', C['green_stroke'],
        '키워드 매칭 → 즉시 차단', '', text1_size=9, text1_color='#04342C')
    box(ax, 4.9, 3.85, 3.7, 0.5, '#9FE1CB', C['green_stroke'],
        'jump: "end" → LLM 비용 $0', '', text1_size=9, text1_color='#04342C')

    # badges (green)
    box(ax, 4.9, 3.62, 1.6, 0.18, C['olive_fill'], C['olive_stroke'],
        '빠름 · 저렴', '', text1_size=8, text1_color=C['olive_text'])
    ax.text(5.7, 3.4, 'LLM 호출 없음', ha='center', fontsize=8, color=C['label'])
    box(ax, 6.9, 3.62, 1.7, 0.18, C['gray_fill'], C['gray_stroke'],
        '단순 패턴', '', text1_size=8, text1_color=C['gray_text'])
    ax.text(7.75, 3.4, '키워드 매칭만', ha='center', fontsize=8, color=C['label'])

    arrow(ax, 6.75, 3.6, 6.75, 3.25)

    # 모델 기반 가드레일 (red/orange)
    bg4 = FancyBboxPatch((4.7, 0.8), 4.1, 2.35, boxstyle="round,pad=0,rounding_size=0.4",
                         facecolor=C['red_fill'], edgecolor=C['red_stroke'], lw=0.8, zorder=1)
    ax.add_patch(bg4)
    ax.text(6.75, 2.93, '모델 기반 가드레일', ha='center', fontsize=11, fontweight='bold',
            color=C['red_text'], zorder=3)
    ax.text(6.75, 2.63, '@after_agent · AI가 직접 평가', ha='center', fontsize=9,
            color=C['red_stroke'], zorder=3)

    box(ax, 4.9, 2.2, 3.7, 0.35, '#F5C4B3', C['red_stroke'],
        '"leaked" 감지 → 힌트로 교정', '', text1_size=9, text1_color='#4A1B0C')
    box(ax, 4.9, 1.75, 1.6, 0.35, C['red_fill'], C['red_stroke'],
        '섬세함', '', text1_size=9, text1_color=C['red_text'])
    ax.text(5.7, 1.55, '미묘한 패턴 감지', ha='center', fontsize=8, color=C['label'])
    box(ax, 6.8, 1.75, 1.8, 0.35, C['gray_fill'], C['gray_stroke'],
        '비용 발생', '', text1_size=9, text1_color=C['gray_text'])
    ax.text(7.7, 1.55, 'LLM 호출 필요', ha='center', fontsize=8, color=C['label'])

    # Bottom bar
    note = FancyBboxPatch((0.4, 0.12), 8.2, 0.5, boxstyle="round,pad=0,rounding_size=0.25",
                          facecolor=C['orange_fill'], edgecolor=C['orange_stroke'], lw=0.6, zorder=2)
    ax.add_patch(note)
    ax.text(4.5, 0.37, 'POC(가능성증명) → POV(가치증명)를 위한 핵심 기술',
            ha='center', va='center', fontsize=9, color=C['orange_text'], zorder=3)

    plt.tight_layout(pad=0.3)
    plt.savefig(os.path.join(OUT, 'diagram_05_memory_guardrails.png'), dpi=150, bbox_inches='tight',
                facecolor=C['bg'])
    plt.close()
    print("diagram_05 saved")


if __name__ == '__main__':
    make_diagram_01()
    make_diagram_02()
    make_diagram_03()
    make_diagram_04()
    make_diagram_05()
    print("All diagrams generated!")
