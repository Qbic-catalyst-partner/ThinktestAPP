# CustomModulesQuestionsGenerator.py

import psycopg2

meta_schema = "meta"
question_table = "question"
modules_table = "modules"
custommodules_schema = "custommodules"
config_table = "config"

# --- NEW: on-demand connector with keepalives ---
database = None
def get_db():
    global database
    if database is None or database.closed != 0:
        database = psycopg2.connect(
            dbname="thinktestdb",
            user="Thinktest",
            password="Thinktest2025",
            host="thinktestsdb.c3sk8iamux7s.ap-south-1.rds.amazonaws.com",
            port="5432",
            connect_timeout=5,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        database.autocommit = True
    return database

def executeQuery(query):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    except psycopg2.OperationalError:
        # connection likely dropped; reconnect once and retry
        conn = get_db()
        with conn.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()

def fetchCustomModuleQuestions_for_attempt(attempt_id):
    # Fetch all config_id associated with the given attempt_id
    query_configs = f"""
    SELECT config_id, subject_id, module_id, difficulty_level, question_count
    FROM {custommodules_schema}.{config_table}
    WHERE attempt_id = {attempt_id}
    """
    configs = executeQuery(query_configs)

    selected_questions = []

    # For each config, fetch the questions based on subject_id, module_id, and difficulty_level
    for config in configs:
        config_id, subject_id, module_id, difficulty_level, question_count = config

        query_questions = f"""
        SELECT q_id, direction_id, question_description, answer_options, choice_type, max_score, correct_option, solution_explanation, multi_select
        FROM {meta_schema}.{question_table}
        WHERE subject_id = {subject_id}
          AND module_id = {module_id}
          AND difficulty_level = {difficulty_level}
        ORDER BY RANDOM()
        LIMIT {question_count}
        """
        question_results = executeQuery(query_questions)
        for result in question_results:
            questions = {
                'q_id': result[0],
                'direction_id': result[1],
                'question_description': result[2],
                'answer_options': result[3],
                'choice_type': result[4],
                'max_score': result[5],
                'correct_option': result[6],
                'solution_explanation': result[7], 
                'multi_select': result[8],    
            }
            selected_questions.append(questions)

    return selected_questions