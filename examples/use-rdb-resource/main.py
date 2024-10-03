from myvanna import generate_sql_from_prompt, MyVanna
from openssa import DANA, DbResource
from dotenv import load_dotenv

load_dotenv()

def get_or_create_agent(query) -> DANA:
    return DANA(
        resources=[DbResource(query=query)]
    )

def solve(question, query) -> str:
    agent = get_or_create_agent(query)
    try:
        return agent.solve(problem=question)
    except Exception as err:
        return f'ERROR: {err}'

if __name__ == '__main__':
    QUESTION = (
        "Can you list the products in order of sales volume from highest to lowest?"
    )

    query = generate_sql_from_prompt(QUESTION)
    answer = solve(QUESTION, query)

    print('--------------------------------')
    print(answer)
    print('--------------------------------')
    print(query)
    print('--------------------------------')
