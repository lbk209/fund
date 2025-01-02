from dash import html

# split text by line feed using html_comp such as html.P, html.Li, etc
break_line = lambda text, html_comp: [html_comp(line.strip()) for line in text.strip().split("\n") if line.strip()]

def extract_topics(topic_i, heading=html.H6, item=html.Li, 
                   style_heading={'color':'slategray', 'font-weight':'bold'}, 
                   style_content={'margin-top': '20px', 'line-height': '200%'}):
    """
    return heading and list of item component from topic_i
    topic_i: dict of title and content
    heading: ex) html.H6
    item: ex) html.Li, html.P
    """
    func = lambda x: break_line(x, item) if isinstance(x, str) else [item(x)]
    cont = [[heading(k, style=style_heading), *func(v)] for k,v in topic_i.items()]
    return html.Div(
        [html.Div(x, style=style_content) for x in cont],
    )
    

email = 'leebaekku209@gmail.com'

about = """
개인형 퇴직연금(IRP)과 연금저축의 수많은 펀드 어떻게 골라야 할까?
쉽고 빠르게 펀드를 비교할 수 없을까?
업데이트는 매월 초.
"""

disclaimer = """
본 사이트는 투자 권유를 제공하지 않으며, 제공되는 정보의 정확성과 완전성을 보장하지 않습니다.
수수료와 세금은 수익률에 영향을 미칠 수 있으며, 투자 결정 및 그에 따른 결과는 전적으로 투자자 본인의 책임입니다.
"""

# list of topic groups each of which is dict of title and contents
topics = [
    {'왜 펀드는 가격 대신 수익률로 추이를 표시하는가?': """
펀드는 주기적으로 가격을 조정하기 때문에 주식과 달리 가격 대신 수익률로 추이를 표시
수익률은 기간에 따라 다르므로 펀드 비교시 연환산 수익률(CAGR)을 사용해야 함
""",
    '목표 시점에 맞춰 위험 자산 비중을 줄여가는 펀드 TDF':"""
올해 목표시점에 도달한 TDF2025 펀드들의 경우 연환산 수익률은 5% 미만
목표시점까지 25년 남아서 위험 자산 비중이 높은 TDF2050 펀드들의 경우 현재까지 연환산 수익률은 5~8%
이상 수익률은 공히 수수료 적용, 세금 미적용
수수료는 총 보수(연)를 일정 기간에 나눠 적용. 자세한 사항은 각 펀드 투자설명서 확인.
자세한 펀드별 수익률은 가격, 수익률 탭에서 확인
"""},
    {'TDF는 3년 이상 보유할 것을 추천': """
매수 시점에 따라서는 1년 후 손해 가능성도 있지만 3년 후에는 수익 확률이 높아진다 (아래 표 참고)
3년 보유 후 수익 확률이 97% 이상인 TDF는 47개 중 8개 (베이지안 추정 적용)
"""},
]
contents = dict(
    info = dict(
        about = about,
        disclaimer = disclaimer,
        email = email
    ),
    topics = topics
)