import os, re, secrets
from datetime import datetime
from functools import wraps
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('HR_SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///recruitment.db').replace('postgres://','postgresql+psycopg://').replace('postgresql://','postgresql+psycopg://') if os.environ.get('DATABASE_URL') else 'sqlite:///recruitment.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id=db.Column(db.Integer,primary_key=True); username=db.Column(db.String(120),unique=True,nullable=False); password_hash=db.Column(db.String(255),nullable=False); role=db.Column(db.String(30),default='Recruiter'); active=db.Column(db.Boolean,default=True)
class Candidate(db.Model):
    id=db.Column(db.Integer,primary_key=True); name=db.Column(db.String(200),nullable=False); email=db.Column(db.String(255)); phone=db.Column(db.String(80)); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Job(db.Model):
    id=db.Column(db.Integer,primary_key=True); title=db.Column(db.String(200),nullable=False); location=db.Column(db.String(200)); shift=db.Column(db.String(200)); status=db.Column(db.String(40),default='Open'); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Application(db.Model):
    id=db.Column(db.Integer,primary_key=True); candidate_id=db.Column(db.Integer,db.ForeignKey('candidate.id'),nullable=False); job_id=db.Column(db.Integer,db.ForeignKey('job.id')); role=db.Column(db.String(200)); source=db.Column(db.String(80)); salary=db.Column(db.String(80)); experience=db.Column(db.String(80)); notice_period=db.Column(db.String(80)); status=db.Column(db.String(80),default='New Application'); recommendation=db.Column(db.String(40),default='NEW'); reason=db.Column(db.String(255)); notes=db.Column(db.Text); created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Event(db.Model):
    id=db.Column(db.Integer,primary_key=True); application_id=db.Column(db.Integer,db.ForeignKey('application.id')); stage=db.Column(db.String(120)); outcome=db.Column(db.String(80)); reason=db.Column(db.String(255)); notes=db.Column(db.Text); created_at=db.Column(db.DateTime,default=datetime.utcnow)

STAGES=['New Application','Invite Sent','First Interview','First Follow Up','Second Follow Up','Final Follow Up','Technical Assessment','Project Assessment','Second Interview','Final Interview','Selected','Rejected']
SOURCES=['Naukri','LinkedIn','Wellfound','WhatsApp','Referral','Company Website','Imported CSV','Other']
HARD=['Project Assessment Failed','Technical Assessment Failed','Technical Interview Failed','HR Interview Failed','Experience Mismatch','Salary Mismatch']
REVIEW=['Interview No Show','Interview Not Scheduled','Project Assessment Not Submitted','No Response','Candidate Withdrew']

BASE='''<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Hire Reactor Recruitment</title><style>body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f8fb;color:#243342}nav{background:#243444;color:#fff;padding:14px 24px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}nav a{color:#fff;text-decoration:none}.brand{font-weight:700;margin-right:12px}.wrap{max-width:1200px;margin:24px auto;padding:0 18px}.card{background:#fff;border-radius:12px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px #00000010}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #e7edf2;text-align:left}th{background:#f7fafc}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.metric{font-size:28px;font-weight:700}.btn{display:inline-block;background:#2f9be3;color:#fff;border:0;border-radius:7px;padding:9px 14px;text-decoration:none;cursor:pointer}.danger{background:#b44}.input,select,textarea{width:100%;box-sizing:border-box;padding:9px;border:1px solid #ccd7e0;border-radius:7px;margin:5px 0 12px}label{font-weight:600;font-size:13px}.muted{color:#6b7a86}.pill{padding:4px 8px;border-radius:12px;background:#edf5fb;font-size:12px}.login{max-width:420px;margin:10vh auto}.flash{padding:10px;background:#fff3cd;border-radius:7px;margin-bottom:12px}</style></head><body>{% if session.get('user') %}<nav><span class=brand>Hire Reactor TA</span><a href="{{url_for('dashboard')}}">Dashboard</a><a href="{{url_for('candidates')}}">Candidates</a><a href="{{url_for('jobs')}}">Jobs</a><a href="{{url_for('applications')}}">Applications</a><a href="{{url_for('logout')}}">Logout</a></nav>{% endif %}<main class=wrap>{% with messages=get_flashed_messages() %}{% for m in messages %}<div class=flash>{{m}}</div>{% endfor %}{% endwith %}{% block content %}{% endblock %}</main></body></html>'''

def page(body,title=''):
    return render_template_string(BASE.replace('{% block content %}{% endblock %}',body),title=title)
def login_required(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get('user'): return redirect(url_for('login',next=request.path))
        return f(*a,**k)
    return w

def norm(v): return re.sub(r'[^a-z0-9]','', (v or '').lower())
def recommendation(reason):
    r=(reason or '').lower()
    if any(x.lower() in r for x in HARD): return 'DO NOT PROCEED'
    if any(x.lower() in r for x in REVIEW): return 'REVIEW'
    return 'REVIEW'

@app.before_request
def init():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        p=os.environ.get('HR_ADMIN_PASSWORD','ChangeMe-2026!')
        db.session.add(User(username='admin',password_hash=generate_password_hash(p),role='Admin')); db.session.commit()

@app.route('/health')
def health(): return {'status':'ok'}
@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=User.query.filter_by(username=request.form.get('username','').strip()).first()
        if u and u.active and check_password_hash(u.password_hash,request.form.get('password','')):
            session['user']=u.username; session['role']=u.role; return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password.')
    return page('''<div class=login><div class=card><h1>Hire Reactor Recruitment</h1><p class=muted>Talent Acquisition Management System</p><form method=post><label>Username</label><input class=input name=username required><label>Password</label><input class=input type=password name=password required><button class=btn>Sign in</button></form></div></div>''')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return page('''<h1>Recruitment Dashboard</h1><div class=grid><div class=card><div class=muted>Candidates</div><div class=metric>{{c}}</div></div><div class=card><div class=muted>Open Jobs</div><div class=metric>{{j}}</div></div><div class=card><div class=muted>Applications</div><div class=metric>{{a}}</div></div><div class=card><div class=muted>Selected</div><div class=metric>{{s}}</div></div></div><div class=card><h2>Recent Applications</h2><table><tr><th>Candidate</th><th>Role</th><th>Status</th><th>Recommendation</th></tr>{% for x in recent %}<tr><td>{{x[0]}}</td><td>{{x[1]}}</td><td>{{x[2]}}</td><td>{{x[3]}}</td></tr>{% endfor %}</table></div>''',).replace('</main>','') if False else render_template_string(BASE.replace('{% block content %}{% endblock %}','''<h1>Recruitment Dashboard</h1><div class=grid><div class=card><div class=muted>Candidates</div><div class=metric>{{c}}</div></div><div class=card><div class=muted>Open Jobs</div><div class=metric>{{j}}</div></div><div class=card><div class=muted>Applications</div><div class=metric>{{a}}</div></div><div class=card><div class=muted>Selected</div><div class=metric>{{s}}</div></div></div><div class=card><h2>Recent Applications</h2><table><tr><th>Candidate</th><th>Role</th><th>Status</th><th>Recommendation</th></tr>{% for x in recent %}<tr><td>{{x[0]}}</td><td>{{x[1]}}</td><td>{{x[2]}}</td><td>{{x[3]}}</td></tr>{% endfor %}</table></div>'''),c=Candidate.query.count(),j=Job.query.filter_by(status='Open').count(),a=Application.query.count(),s=Application.query.filter_by(status='Selected').count(),recent=[(Candidate.query.get(x.candidate_id).name,x.role,x.status,x.recommendation) for x in Application.query.order_by(Application.created_at.desc()).limit(10)])

@app.route('/candidates')
@login_required
def candidates():
    q=request.args.get('q','').strip(); rows=Candidate.query.order_by(Candidate.created_at.desc())
    if q: rows=rows.filter((Candidate.name.ilike('%'+q+'%'))|(Candidate.email.ilike('%'+q+'%'))|(Candidate.phone.ilike('%'+q+'%')))
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>Candidates</h1><form><input class=input name=q value="{{q}}" placeholder="Search name, email or phone"><button class=btn>Search</button> <a class=btn href="{{url_for('add_candidate')}}">Add Candidate</a></form></div><div class=card><table><tr><th>Name</th><th>Email</th><th>Phone</th><th>Applications</th></tr>{% for x in rows %}<tr><td><a href="{{url_for('candidate',id=x.id)}}">{{x.name}}</a></td><td>{{x.email or ''}}</td><td>{{x.phone or ''}}</td><td>{{Application.query.filter_by(candidate_id=x.id).count()}}</td></tr>{% endfor %}</table></div>'''),rows=rows.all(),q=q,Application=Application)

@app.route('/candidates/add',methods=['GET','POST'])
@login_required
def add_candidate():
    if request.method=='POST':
        email=request.form.get('email','').strip(); phone=request.form.get('phone','').strip()
        existing=Candidate.query.filter((Candidate.email==email)&(Candidate.email!='')).first() if email else None
        if not existing and phone: existing=Candidate.query.filter_by(phone=phone).first()
        if existing:
            flash('Existing candidate found. A new application can be added to the existing record.'); return redirect(url_for('candidate',id=existing.id))
        x=Candidate(name=request.form.get('name','').strip(),email=email,phone=phone); db.session.add(x); db.session.commit(); return redirect(url_for('candidate',id=x.id))
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>Add Candidate</h1><form method=post><label>Name</label><input class=input name=name required><label>Email</label><input class=input name=email type=email><label>Phone</label><input class=input name=phone><button class=btn>Save Candidate</button></form></div>'''))

@app.route('/candidate/<int:id>')
@login_required
def candidate(id):
    c=Candidate.query.get_or_404(id); apps=Application.query.filter_by(candidate_id=id).order_by(Application.created_at.desc()).all(); return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>{{c.name}}</h1><p>{{c.email or ''}} · {{c.phone or ''}}</p><a class=btn href="{{url_for('new_application',candidate_id=c.id)}}">New Application</a></div><div class=card><h2>Application History</h2><table><tr><th>Role</th><th>Source</th><th>Status</th><th>Recommendation</th><th>Reason</th></tr>{% for x in apps %}<tr><td><a href="{{url_for('application',id=x.id)}}">{{x.role}}</a></td><td>{{x.source}}</td><td>{{x.status}}</td><td>{{x.recommendation}}</td><td>{{x.reason or ''}}</td></tr>{% endfor %}</table></div>'''),c=c,apps=apps)

@app.route('/applications')
@login_required
def applications():
    rows=Application.query.order_by(Application.created_at.desc()).all(); data=[(x,Candidate.query.get(x.candidate_id)) for x in rows]
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>Applications</h1><a class=btn href="{{url_for('add_candidate')}}">Add Candidate</a></div><div class=card><table><tr><th>Candidate</th><th>Role</th><th>Source</th><th>Status</th><th>Recommendation</th></tr>{% for x,c in data %}<tr><td><a href="{{url_for('candidate',id=c.id)}}">{{c.name}}</a></td><td><a href="{{url_for('application',id=x.id)}}">{{x.role}}</a></td><td>{{x.source}}</td><td>{{x.status}}</td><td>{{x.recommendation}}</td></tr>{% endfor %}</table></div>'''),data=data)

@app.route('/application/new/<int:candidate_id>',methods=['GET','POST'])
@login_required
def new_application(candidate_id):
    c=Candidate.query.get_or_404(candidate_id); jobs=Job.query.filter_by(status='Open').all()
    if request.method=='POST':
        reason=request.form.get('reason','').strip(); job_id=request.form.get('job_id') or None; job=Job.query.get(job_id) if job_id else None
        x=Application(candidate_id=c.id,job_id=job.id if job else None,role=request.form.get('role') or (job.title if job else ''),source=request.form.get('source'),salary=request.form.get('salary'),experience=request.form.get('experience'),notice_period=request.form.get('notice'),status=request.form.get('status') or 'New Application',reason=reason,recommendation='NEW' if not Application.query.filter_by(candidate_id=c.id).first() else recommendation(reason),notes=request.form.get('notes'))
        db.session.add(x); db.session.flush(); db.session.add(Event(application_id=x.id,stage=x.status,outcome='Pending',reason=reason)); db.session.commit(); return redirect(url_for('application',id=x.id))
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>New Application — {{c.name}}</h1><form method=post><label>Job</label><select name=job_id><option value="">Custom / select role below</option>{% for j in jobs %}<option value={{j.id}}>{{j.title}}</option>{% endfor %}</select><label>Role</label><input class=input name=role required><label>Source</label><select name=source>{% for s in sources %}<option>{{s}}</option>{% endfor %}</select><label>Salary</label><input class=input name=salary><label>Experience</label><input class=input name=experience><label>Notice Period</label><input class=input name=notice><label>Status</label><select name=status>{% for s in stages %}<option>{{s}}</option>{% endfor %}</select><label>Reason / previous outcome</label><input class=input name=reason><label>Notes</label><textarea class=input name=notes></textarea><button class=btn>Create Application</button></form></div>'''),c=c,jobs=jobs,sources=SOURCES,stages=STAGES)

@app.route('/application/<int:id>',methods=['GET','POST'])
@login_required
def application(id):
    x=Application.query.get_or_404(id); c=Candidate.query.get(x.candidate_id); events=Event.query.filter_by(application_id=id).order_by(Event.created_at.desc()).all()
    if request.method=='POST':
        x.status=request.form.get('status'); x.reason=request.form.get('reason',''); x.notes=request.form.get('notes',''); x.recommendation=recommendation(x.reason) if x.status!='New Application' else x.recommendation; db.session.add(Event(application_id=id,stage=x.status,outcome=request.form.get('outcome','Pending'),reason=x.reason,notes=x.notes)); db.session.commit(); flash('Application updated.'); return redirect(url_for('application',id=id))
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>{{c.name}} — {{x.role}}</h1><p><b>Recommendation:</b> {{x.recommendation}} · <b>Status:</b> {{x.status}}</p><p>{{c.email or ''}} · {{c.phone or ''}}</p></div><div class=card><h2>Update Stage</h2><form method=post><label>Status</label><select name=status>{% for s in stages %}<option {% if s==x.status %}selected{% endif %}>{{s}}</option>{% endfor %}</select><label>Outcome</label><select name=outcome>{% for s in outcomes %}<option>{{s}}</option>{% endfor %}</select><label>Reason</label><input class=input name=reason value="{{x.reason or ''}}"><label>Notes</label><textarea class=input name=notes>{{x.notes or ''}}</textarea><button class=btn>Save Update</button></form></div><div class=card><h2>History</h2><table><tr><th>Date</th><th>Stage</th><th>Outcome</th><th>Reason</th></tr>{% for e in events %}<tr><td>{{e.created_at}}</td><td>{{e.stage}}</td><td>{{e.outcome}}</td><td>{{e.reason or ''}}</td></tr>{% endfor %}</table></div>'''),x=x,c=c,events=events,stages=STAGES,outcomes=['Pending','Passed','Failed','Scheduled','Completed','Selected','Rejected','Withdrawn','No Show'])

@app.route('/jobs')
@login_required
def jobs():
    rows=Job.query.order_by(Job.created_at.desc()).all(); return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>Jobs</h1><a class=btn href="{{url_for('new_job')}}">Create Job</a></div><div class=card><table><tr><th>Role</th><th>Location</th><th>Shift</th><th>Status</th></tr>{% for j in rows %}<tr><td>{{j.title}}</td><td>{{j.location}}</td><td>{{j.shift}}</td><td>{{j.status}}</td></tr>{% endfor %}</table></div>'''),rows=rows)
@app.route('/jobs/new',methods=['GET','POST'])
@login_required
def new_job():
    if request.method=='POST':
        j=Job(title=request.form.get('title'),location=request.form.get('location'),shift=request.form.get('shift'),status='Open'); db.session.add(j); db.session.commit(); return redirect(url_for('jobs'))
    return render_template_string(BASE.replace('{% block content %}{% endblock %}','''<div class=card><h1>Create Job</h1><form method=post><label>Job Title</label><input class=input name=title required><label>Location</label><input class=input name=location><label>Shift</label><input class=input name=shift><button class=btn>Create Job</button></form></div>'''))

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
