from flask import Flask, jsonify, render_template, request, session, redirect, url_for
import oracledb

app = Flask(__name__)
app.secret_key = 'vaxtrack_secret_2024'

def get_connection():
    connection = oracledb.connect(
        user="System",
        password="asma@123",
        dsn="localhost:1521/orcl1"
    )
    return connection

# ─── LOGIN ────────────────────────────────────────────
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, username, role, ref_id FROM Users WHERE username=:1 AND password=:2",
            [username, password]
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row:
            session['user'] = {
                'id': row[0], 'username': row[1],
                'role': row[2], 'ref_id': row[3]
            }
            return jsonify({'success': True, 'role': row[2]})
        return jsonify({'success': False, 'message': 'Galat username ya password!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('index'))
    role = session['user']['role']
    if role == 'admin':
        return render_template('admin.html', user=session['user'])
    elif role == 'doctor':
        return render_template('doctor.html', user=session['user'])
    elif role == 'patient':
        return render_template('patient.html', user=session['user'])
    return redirect(url_for('index'))

# ─── ADMIN APIs ───────────────────────────────────────
@app.route('/api/stats')
def get_stats():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM Patient")
    total_patients = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Vaccine")
    total_vaccines = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Appointment")
    total_appointments = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Appointment WHERE status='Pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM Vaccination_Record")
    total_doses = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return jsonify({
        "total_patients": total_patients, "total_vaccines": total_vaccines,
        "total_appointments": total_appointments,
        "pending_appointments": pending, "total_doses": total_doses
    })

@app.route('/api/patients')
def get_patients():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id, name, gender, TO_CHAR(dob,'DD Mon YYYY') as dob, phone, address FROM Patient")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/patients', methods=['POST'])
def add_patient():
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT NVL(MAX(patient_id),0)+1 FROM Patient")
    new_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO Patient VALUES (:1,:2,:3,TO_DATE(:4,'YYYY-MM-DD'),:5,:6)",
        [new_id, data['name'], data['gender'], data['dob'], data['phone'], data['address']]
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True, 'id': new_id})

@app.route('/api/patients/<int:pid>', methods=['DELETE'])
def delete_patient(pid):
    if 'user' not in session or session['user']['role'] != 'admin':
        return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Patient WHERE patient_id=:1", [pid])
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/vaccines')
def get_vaccines():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Vaccine")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/centers')
def get_centers():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Center")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/appointments')
def get_appointments():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    role = session['user']['role']
    ref_id = session['user']['ref_id']
    if role == 'patient':
        cursor.execute("""
            SELECT a.appointment_id, p.name AS patient_name, c.center_name,
                   TO_CHAR(a.appointment_date,'DD Mon YYYY') AS appt_date, a.status
            FROM Appointment a JOIN Patient p ON a.patient_id=p.patient_id
            JOIN Center c ON a.center_id=c.center_id
            WHERE a.patient_id=:1""", [ref_id])
    else:
        cursor.execute("""
            SELECT a.appointment_id, p.name AS patient_name, c.center_name,
                   TO_CHAR(a.appointment_date,'DD Mon YYYY') AS appt_date, a.status
            FROM Appointment a JOIN Patient p ON a.patient_id=p.patient_id
            JOIN Center c ON a.center_id=c.center_id""")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/records')
def get_records():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    role = session['user']['role']
    ref_id = session['user']['ref_id']
    base_q = """
        SELECT vr.record_id, p.name AS patient_name, v.vaccine_name,
               d.doctor_name, c.center_name, vr.dose_no,
               TO_CHAR(vr.vaccination_date,'DD Mon YYYY') AS vax_date
        FROM Vaccination_Record vr
        JOIN Patient p ON vr.patient_id=p.patient_id
        JOIN Vaccine v ON vr.vaccine_id=v.vaccine_id
        JOIN Doctor d ON vr.doctor_id=d.doctor_id
        JOIN Center c ON vr.center_id=c.center_id"""
    if role == 'patient':
        cursor.execute(base_q + " WHERE vr.patient_id=:1", [ref_id])
    elif role == 'doctor':
        cursor.execute(base_q + " WHERE vr.doctor_id=:1", [ref_id])
    else:
        cursor.execute(base_q)
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/records', methods=['POST'])
def add_record():
    if 'user' not in session or session['user']['role'] not in ['admin','doctor']:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT record_seq.NEXTVAL FROM dual")
    new_id = cursor.fetchone()[0]
    cursor.execute(
        "INSERT INTO Vaccination_Record VALUES (:1,:2,:3,:4,:5,:6,SYSDATE)",
        [new_id, data['patient_id'], data['vaccine_id'],
         data['doctor_id'], data['center_id'], data['dose_no']]
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'success': True})

@app.route('/api/doctors')
def get_doctors():
    if 'user' not in session: return jsonify({'error': 'unauthorized'}), 401
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.doctor_id, d.doctor_name, d.specialization, c.center_name
        FROM Doctor d JOIN Center c ON d.center_id=c.center_id""")
    columns = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([dict(zip(columns, row)) for row in rows])

@app.route('/api/session')
def get_session():
    if 'user' in session:
        return jsonify(session['user'])
    return jsonify({}), 401

if __name__ == '__main__':
    app.run(debug=True, port=5000)