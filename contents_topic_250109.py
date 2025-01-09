from dash import html
   

# list of topic groups each of which is dict of title and contents
topics = [
    {'왜 펀드는 가격 대신 수익률로 추이를 표시하는가?': """
펀드는 주기적으로 가격을 조정하기 때문에 주식과 달리 가격 대신 수익률로 펀드 성과를 표시
수익률은 기간에 따라 다르므로 펀드 비교시 연환산 수익률(CAGR)을 사용해야 함
""",
    '목표 시점에 맞춰 위험 자산 비중을 줄여가는 펀드 TDF': """
올해 목표시점에 도달한 TDF2025 펀드들의 경우 연환산 수익률은 5% 미만
목표시점까지 많이 남아 위험 자산 비중이 높은 TDF2050 펀드들의 경우 현재까지 연환산 수익률은 5~8%
이상 수익률은 수수료 적용, 세금 미적용
수수료는 1년 단위 총 보수를 일정 기간에 나눠 적용. 자세한 사항은 각 펀드 투자설명서 확인
자세한 펀드별 수익률은 가격, 수익률 탭에서 확인
"""},
    {'TDF는 3년 이상 보유하는 것이 유리': """
매수 시점에 따라 1년 후 손해 가능성도 있지만 3년 후에는 수익 확률 상승 (표1)
3년 수익률 분포를 추정(베이지안 통계)하고 그 중 손해 확률이 낮은 (하위 3% 추정 수익률이 가장 큰) TDF를 선정 (그림1 참고)
3년 수익률 평균이 높았던 TDF를 선정(빈도주의 통계)하고 수익률 분포를 추정(베이지안): 더 높은 수익률도 가능하나 손해 가능성도 존재 (그림2 참고)
"""},
]

img_style={#'width':'100%', 
           'max-width':'100%', 
           'height':'auto'}
set_img = lambda img, alt: html.Img(src=f'/assets/{img}.png', alt=alt, style=img_style)
images = [
    {'그림1: 손해 확률이 낮은 TDF의 3년 수익률 추정': set_img('tdf_hdi3', '3-year rate of return estimation 1')},
    {'그림2: 3년 수익률 평균이 높았던 TDF의 3년 수익률 추정': set_img('tdf_frequentist', '3-year rate of return  estimation 2')}
]


