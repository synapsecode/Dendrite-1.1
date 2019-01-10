from flask import render_template, url_for, flash, redirect, request, send_file
from Dendrite import app, db, bcrypt
from Dendrite.forms import RegistrationForm, LoginForm, CreateTender, CreateAsset
from Dendrite.models import User, Contract
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug import secure_filename
import os
from Dendrite.bigchainuploader import CreateAndUploadGenesisBlock

#GLOBAL STATE VARIABLES
filter_on = False
filter_ops = None
properties = []

# HELPER FUNCTIONS
# Change the status of the Contract
def change_status(c_id, func):
	if func == "ack":
		x = Contract.query.filter_by(contract_id=c_id).first()
		x.status = "Acknowledged"
		db.session.commit()
		flash(f'Contract {c_id} has been Acknowledged Successfully!', 'primary')
	elif func == "a":
		x = Contract.query.filter_by(contract_id=c_id).first()
		x.status = "Approved"
		db.session.commit()
		flash(f'Contract {c_id} has been Approved Successfully!', 'success')
	elif func == "r":
		x = Contract.query.filter_by(contract_id=c_id).first()
		x.status = "Rejected"
		db.session.commit()
		flash(f'Contract {c_id} has been Rejected', 'danger')

# Create the Actual Tender and save it in the Database
def create_tender(form):
	filename = secure_filename(form.file.data.filename)
	form.file.data.save(f'Dendrite/static/Contracts/{filename}')
	# Creating the Database Object
	contract = Contract(contract_id=form.cid.data, contract_date=form.doi.data,
						contract_address=form.vendor_address.data, username=current_user.username, 
						role=current_user.role, contract_file=filename)
	db.session.add(contract)
	db.session.commit()
	flash(f"Contract '{form.cid.data}' created successfully!", 'success')

def create_genesis_asset(name, quantity, properties, contracts):
	asset = {}
	for p in properties:
		asset[(p.get('key')).replace(' ', '_')] = p.get('value')
	if CreateAndUploadGenesisBlock(asset, name, quantity, contracts):
		flash(f"Successfully Deployed Asset '{name}'", "success")
	else:
		flash(f"Error occured while trying to Deploy Asset '{name}'", 'danger')
# --------------------------------------------------------------------------------------------------------------------

@app.route("/")
def homepage():
	return render_template('home.html', name='home', title='Dendrite - Home')

@app.route("/login", methods=['GET', 'POST'])
def loginpage():	
	if current_user.is_authenticated:
		return redirect(url_for('homepage'))
	form = LoginForm()
	if form.validate_on_submit():
		role = dict(form.role.choices).get(form.role.data)
		user = User.query.filter_by(username=form.username.data, role=role).first()
		if user and bcrypt.check_password_hash(user.password, form.password.data):
			login_user(user)
			if role == "Vendor":
				return redirect(url_for('vendorpage'))
			elif role == "Company":
				return redirect(url_for('vendor_address'))
			elif role == "Manufacturer":
				return redirect(url_for('manufacturerpage'))
			else:
				return redirect(url_for('homepage'))
		else:
			flash('Invalid Credentials, Please try again', 'danger')
	return render_template("login.html", name='login', title="Dendrite - Login", form=form)

@app.route("/register", methods=['GET', 'POST'])
def registerpage():
	if current_user.is_authenticated:
		return redirect(url_for('homepage'))
	form = RegistrationForm()
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user = User(username=form.username.data, role=(dict(form.role.choices).get(form.role.data)), password=hashed_password)
		db.session.add(user)
		db.session.commit()
		flash(f"Account '{form.username.data}' created successfully!", 'success')
		return redirect(url_for('loginpage'))
	else:
		return render_template("register.html", name='register', title="Dendrite - Register", form=form)

@app.route("/logout")
def logout():
	logout_user()
	return redirect(url_for('homepage'))

@app.route("/checkorigin")
def checkorigin():
	return render_template("checkorigin.html", name='co', title="Check Origin")

@app.route("/vendors")
@login_required
def vendorpage():
	contracts = Contract.query.filter_by(username=current_user.username, role=current_user.role)
	return render_template("vendordashboard.html", name='vendor', title="Vendor Dashboard", contracts=contracts)


@app.route("/manufacturer/createasset", methods=['GET', 'POST'])
@login_required
def createasset():
	# ------------Getting all the Properties Posted by the Manufacturer----------
	global properties
	key = request.args.get('key')
	value = request.args.get('value')
	kvp = {
		'key': key,
		'value': value
	}
	if key and value not in ('', None, properties) and kvp not in properties:
		properties.append(kvp)
	# print(properties)
	# -----------------------End of Collecting Properties--------------------
	form = CreateAsset()
	if form.validate_on_submit():
		asset_name = form.asset_name.data
		quantity = form.quantity.data
		# print(asset_name)
		ctr_fnames = []
		for f in request.files.getlist('ctr'):
			ctr_fnames.append(secure_filename(f.filename))
		create_genesis_asset(asset_name, quantity, properties, ctr_fnames)
		return redirect(url_for('manufacturerpage'))
	return render_template("createassetpage.html", name='ca', title="Create Asset", p=properties, form=form)

@app.route("/manufacturer")
@login_required
def manufacturerpage():
	contracts = Contract.query.filter_by(username=current_user.username, role=current_user.role)
	return render_template("manufacturerdashboard.html", name='manufacturer', title="Manufacturer Dashboard", contracts=contracts)


@app.route("/tenders")
@login_required
def vendor_address():
	# Checking Global value
	contracts = Contract.query.all()
	return render_template("companytender.html", name='company', title="Company Tender Management", contracts=contracts)


# -------------------------------------------------FUNCTION BASED PAGES-----------------------------------------

@app.route("/createcontract", methods=['GET', 'POST'])
@login_required
def create_contract():
	form = CreateTender()
	if form.validate_on_submit():
		# Uploading the Contract
		create_tender(form)
	return render_template("createtender.html", name='cc', title="Create Contract", form=form)
	
# -------------------------------------------------FUNCTION BASED PAGES-----------------------------------------

# -------------------------------------------CONTRACT DESCRIPTION CODE-----------------------------------------

# This is used to Display Each Individual Contract on the Description Panel for the Vendors page
@app.route("/vendors/<c_id>")
@login_required
def vendordesc(c_id):
	contracts = Contract.query.filter_by(username=current_user.username, role=current_user.role)
	c = Contract.query.filter_by(contract_id=c_id).first()
	return render_template("vendordashboard.html", name='vendor', title="Vendor Dashboard", contracts=contracts, cdesc=c)

# This is used to Display Each Individual Contract on the Description Panel for the Company Tenders
@app.route("/tenders/<c_id>")
@login_required
def contractdesc(c_id):
	# Checking Global value
	global filter_on
	global filter_ops
	if filter_on:
		contracts = Contract.query.filter_by(role=filter_ops).all()
	else:
		contracts = Contract.query.all()
	c = Contract.query.filter_by(contract_id=c_id).first()
	return render_template("companytender.html", name='company', title="Company Tender Management", cdesc=c, contracts=contracts)

# This is used to Display Each Individual Contract on the Description Panel for the Manufacturers page
@app.route("/manufacturer/<c_id>")
@login_required
def manufacturerdesc(c_id):
	contracts = Contract.query.filter_by(username=current_user.username, role=current_user.role)
	c = Contract.query.filter_by(contract_id=c_id).first()
	return render_template("manufacturerdashboard.html", name='manufacturer', title="Manufacturer Dashboard", contracts=contracts, cdesc=c)

# -------------------------------------------CONTRACT DESCRIPTION CODE-----------------------------------------

# -------------------------------------------UPLOADING TENDER FROM SERVER--------------------------------------------
# Send Contract file from server
@app.route("/getcontract/<fn>")
def get_contract(fn):
	file = os.path.join(app.root_path, 'static/Contracts', fn)
	return send_file(file)

# -------------------------------------------UPLOADING TENDER FROM SERVER--------------------------------------------

#-------------------------------------------------FILTERING-----------------------------------------------

# This is used to filter the content
@app.route("/tenders/filterquery/<filter>")
@login_required
def filtervendor(filter):
	# Creating Global State variables
	global filter_on
	global filter_ops
	# Assigning them a value
	filter_on = True
	filter_ops = filter
	contracts = Contract.query.filter_by(role=filter).all()
	return render_template("companytender.html", name='company', title="Company Tender Management", contracts=contracts)

# This is used to clear the filtered content
@app.route("/tenders/deletefilterquery")
@login_required
def deletefilters():
	# Reversing Global State value
	global filter_on
	global filter_ops
	filter_on = False
	filter_ops = ''
	return redirect(url_for('vendor_address'))

#--------------------------------------------------FILTERING-----------------------------------------------------

#---------------------------------------------CONTRACT LEVEL FUNCTIONS-----------------------------------------
@app.route("/tenders/<c_id>/<func>")
@login_required
def contractfunctions(c_id, func):
	global filter_on
	global filter_ops
	if current_user.role == "Company":
		# Checking Global value
		if filter_on:
			contracts = Contract.query.filter_by(role=filter_ops).all()
		else:
			contracts = Contract.query.all()
		# Change Status
		change_status(c_id, func)
		return redirect(url_for('vendor_address'))
	else:
		return "Route not accessible"
	c = Contract.query.filter_by(contract_id=c_id).first()
	return render_template("companytender.html", name='company', title="Company Tender Management", cdesc=c, contracts=contracts)

#---------------------------------------------CONTRACT LEVEL FUNCTIONS-----------------------------------------