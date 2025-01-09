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