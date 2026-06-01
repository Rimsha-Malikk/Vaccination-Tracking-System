import oracledb

def get_connection():
    connection = oracledb.connect(
        user="System",
        password="asma@123",
        dsn="localhost/orcl1"
    )
    return connection