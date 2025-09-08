import psycopg2

mocktest_schema = "mocktest"
meta_schema = "meta"
mocktest_config_table = "config"
question_table = "question"
upper_difficulty_level = 5

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

def fetchMockTestQuestions(exam_name,exam_id):

    #Fetch configuration of exam
    exam_config_query = "select * from "+mocktest_schema+"."+mocktest_config_table+" where exam_id = "+str(exam_id)+";"
    exam_config = executeQuery(exam_config_query)

    question_query =""
    for subject_config in exam_config:    
        subject_id = subject_config[1]
        for difficulty_level in range(1,upper_difficulty_level+1):
            if question_query!="":
                question_query+=" UNION ALL "
            question_count = subject_config[2][str(difficulty_level)]
            question_query+="(SELECT * FROM "+meta_schema+"."+question_table+" WHERE subject_id = "+str(subject_id)+" AND difficulty_level = "+str(difficulty_level)+" ORDER BY RANDOM() LIMIT "+str(question_count)+")"

    #Fetch questions
    questions = executeQuery(question_query)

    #Close DB
    # database.close()
    return questions