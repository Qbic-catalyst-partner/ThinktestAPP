import psycopg2

mocktest_schema = "mocktest"
meta_schema = "meta"
mocktest_config_table = "config"
question_table = "question"
upper_difficulty_level = 5

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

    # Set the schema search path
    # cursor.execute("SET search_path TO "+mocktest_schema)
    
    #Execute query    
    cursor.execute(query)
    df = cursor.fetchall()
    cursor.close()
    return df

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