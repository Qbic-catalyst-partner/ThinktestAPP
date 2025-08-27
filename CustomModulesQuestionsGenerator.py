# CustomModulesQuestionsGenerator.py

import psycopg2

meta_schema = "meta"
question_table = "question"
modules_table = "modules"
custommodules_schema = "custommodules"
config_table = "config"

database = psycopg2.connect(
    dbname="thinktestdb",
    user="Thinktest",
    password="Thinktest2025",
    host="thinktestdb.c8pagqo0ygo1.us-east-1.rds.amazonaws.com",
    port="5432"
)

def executeQuery(query):
    # Connect to the PostgreSQL database
    cursor = database.cursor()

    #Execute query    
    cursor.execute(query)
    df = cursor.fetchall()
    cursor.close()
    return df

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
                'max_score': result[4],
                'correct_option': result[5],
                'solution_explanation': result[6],
                'multi_select': result[7],    
            }
            selected_questions.append(questions)

    return selected_questions