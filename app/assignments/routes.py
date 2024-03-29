from flask import render_template, flash, redirect, url_for, request, abort, current_app, session, Response
from flask_login import current_user, login_required

from app.assignments import bp, models, forms
from app.assignments.forms import TurmaCreationForm, AssignmentCreationForm

from app.files import models
from app.models import Assignment, Upload, Comment, Turma, User, AssignmentTaskFile, Enrollment, PeerReviewForm
import app.models

from app import db
from sqlalchemy import or_
import json, zipfile, zipstream, os
from pathlib import Path

import app.assignments.formbuilder

import datetime


########## Student class (turma) methods
@bp.route("/class/create", methods=['GET', 'POST'])
@login_required
def create_class():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		form = forms.TurmaCreationForm()
		if form.validate_on_submit():
			Turma.new_turma_from_form (form)
			flash('Class successfully created!', 'success')
			return redirect(url_for('assignments.class_admin'))
		return render_template('assignments/class_form.html', title='Create new class', form=form)
	abort(403)
	
	
@bp.route("/class/edit/<turma_id>", methods=['GET', 'POST'])
@login_required
def edit_class(turma_id):	
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		turma = Turma.query.get(turma_id)
		form = TurmaCreationForm(obj=turma)
		if form.validate_on_submit():
			form.populate_obj(turma)
			db.session.add(turma)
			db.session.commit()
			flash('Class edited successfully!', 'success')
			return redirect(url_for('assignments.class_admin'))
		return render_template('assignments/class_form.html', title='Edit class', form=form)
	abort(403)

@bp.route("/class/admin")
@login_required
def class_admin():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		classes_array = Turma.query.all()
		return render_template('assignments/class_admin.html', title='Class admin', classes_array = classes_array)
	abort (403)
	
	
@bp.route("/class/enrollment/<class_id>")
@login_required
def manage_enrollment(class_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		class_enrollment = app.assignments.models.get_class_enrollment_from_class_id(class_id)
		return render_template('assignments/class_enrollment.html', title='Class enrollment', class_enrollment = class_enrollment)
	abort (403)
			
			
@bp.route("/class/enrollment/remove/<enrollment_id>")
@login_required
def remove_enrollment(enrollment_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		class_id = Enrollment.query.get(enrollment_id).turma_id
		Enrollment.query.filter(Enrollment.id==enrollment_id).delete()
		db.session.commit()
		flash('Student removed from class!', 'success')
		return redirect(url_for('assignments.manage_enrollment', class_id = class_id))
	abort (403)

@bp.route("/class/delete/<turma_id>")
@login_required
def delete_class(turma_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		Turma.delete_turma_from_id(turma_id)
		flash('Class ' + str(turma_id) + ' has been deleted.', 'success')
		return redirect(url_for('assignments.class_admin'))		
	abort (403)
########################################

# View created assignments status
@bp.route("/view/", methods=['GET', 'POST'])
@login_required
def view_assignments():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		# Get admin view with all assignments
		clean_assignments_array = app.assignments.models.get_all_assignments_info()
		classes = app.assignments.models.get_all_class_info()
		return render_template('assignments/view_assignments.html',
							   assignments_array = clean_assignments_array,
							   admin = True,
							   classes=classes)
	elif current_user.is_authenticated:
		# Get user class
		if Enrollment.query.filter(Enrollment.user_id==current_user.id).first() is not None:
			# Get assignments for this user
			clean_assignments_array = app.assignments.models.get_user_assignment_info (current_user.id)
			return render_template('assignments/view_assignments.html', assignmentsArray = clean_assignments_array)
		else:
			flash('You are not part of any class and can not see any assignments. Ask your tutor for help to join a class.', 'warning')
			return render_template('assignments/view_assignments.html') # User isn't part of any class - display no assignments
	abort (403)


# View created assignments status
@bp.route("/view/<assignment_id>")
@login_required
def view_assignment_details(assignment_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		assignment_turma = Assignment.query.get(assignment_id).target_turma_id
		students_in_class = Enrollment.query.filter(Enrollment.turma_id == assignment_turma).all()
		completed_assignments = Upload.query.filter(Upload.assignment_id == assignment_id).all()
		assignment_detail_info = app.assignments.models.get_assignment_detail_info(assignment_id)
		return render_template('assignments/view_assignment_details.html',
							   completed_assignments = completed_assignments,
							   uncomplete_assignments = len(students_in_class) - len(completed_assignments),
							   assignment_detail_info = assignment_detail_info,
							   assignment_id = assignment_id
							   )
	abort (403)


# Download all uploads of an assignments
@bp.route("/download/<assignment_id>", methods=['GET'])
@login_required
def download_assignment_uploads(assignment_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):	
		z = zipstream.ZipFile(mode='w', compression=zipstream.ZIP_DEFLATED)
		
		# Get list of uploads for this assignment filtered by class
		uploads_and_users = db.session.query(Upload, User).join(
			User, Upload.user_id==User.id).filter(
				Upload.assignment_id==assignment_id).all()
		
		if len(uploads_and_users) < 1:
			flash ('No files have been uploaded for this assignment yet.', 'warning')
			return redirect(url_for('assignments.view_assignment_details', assignment_id=assignment_id))
		else:
			upload_folder = Path(current_app.config['UPLOAD_FOLDER'])
			for upload, user in uploads_and_users:
				filepath = os.path.join(upload_folder, upload.filename)
				filename = user.student_number + ' - ' + user.username + '.' + app.files.models.get_file_extension(upload.original_filename)
				z.write(filepath, arcname = filename)
		
			response = Response(z, mimetype='application/zip')
			# Name the zip file with class and assignment names		
			assignment = Assignment.query.get(assignment_id)
			class_label = Turma.query.get(assignment.target_turma_id).turma_label
			filename = class_label + ' - ' + assignment.title + '.zip'
			response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
			return response		
	abort (403)
	
	

# Admin page to set new assignment
@bp.route("/create", methods=['GET', 'POST'])
@login_required
def create_assignment():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		form = app.assignments.forms.AssignmentCreationForm()
		form.peer_review_form_id.choices = [(peer_review_form.id, peer_review_form.title) for peer_review_form in PeerReviewForm.query.all()]
		form.target_turmas.choices = [(turma.id, turma.turma_label) for turma in Turma.query.all()]
		if form.validate_on_submit():
			app.assignments.models.new_assignment_from_form(form)
			flash('Assignment successfully created!', 'success')
			return redirect(url_for('assignments.view_assignments'))
		return render_template('assignments/assignment_form.html', title='Create Assignment', form=form)
	abort(403)
	
# Admin page to edit assignments
@bp.route("/edit/<assignment_id>", methods=['GET', 'POST'])
@login_required
def edit_assignment(assignment_id):	
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		assignment = Assignment.query.get(assignment_id)
		form = AssignmentCreationForm(obj=assignment)
		form.peer_review_form_id.choices = [(peer_review_form.id, peer_review_form.title) for peer_review_form in PeerReviewForm.query.all()]
		del form.target_turmas, form.assignment_task_file
		if form.validate_on_submit():
			form.populate_obj(assignment)
			db.session.add(assignment)
			db.session.commit()
			flash('Assignment successfully edited!', 'success')
			return redirect(url_for('assignments.view_assignments'))
		return render_template('assignments/assignment_form.html', title='Edit Assignment', form=form)
	abort(403)
	

# Delete all user uploads and comments associated with this assignment
@bp.route("/delete/<assignment_id>", methods=['GET', 'POST'])
@login_required
def delete_assignment(assignment_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		form = app.user.forms.ConfirmationForm()
		try: 
			assignment = Assignment.query.get(assignment_id)
		except:
			flash ('Could not locate the assignment to be deleted.', 'error')
			return redirect(url_for('assignments.view_assignments'))
		confirmation_message = 'Are you sure you want to delete the following assignment: ' + assignment.title + "?"
		if form.validate_on_submit():
			app.assignments.models.delete_assignment_from_id(assignment_id)
			flash('Assignment ' + str(assignment_id) + ' successfully deleted!', 'success')
			return redirect(url_for('assignments.view_assignments'))
		return render_template('confirmation_form.html',
							   title='Delete assignment',
							   confirmation_message = confirmation_message,
							   form=form)
	abort (403)

############# User peer review routes
# Display an empty review feedback form
@bp.route("/review/<assignment_id>", methods=['GET', 'POST'])
def create_peer_review(assignment_id):
	if request.method == 'POST':
		form_contents = json.dumps(request.form)
		# Submit form
		if app.assignments.models.new_peer_review_from_form (form_contents, assignment_id):
			# The database is now updated with the comment - check the total completed comments
			completed_comments = len(Comment.get_completed_peer_reviews_from_user_for_assignment (current_user.id, assignment_id))
			if completed_comments == 1:
				flash('Peer review 1 submitted succesfully!', 'success')
			elif completed_comments == 2:
				flash('Peer review 2 submitted succesfully!', 'success')
			return redirect(url_for('assignments.view_assignments'))
		else: # The user tried to submit a review without a pending review
			flash('You need to download an assignment before you submit a peer review!', 'warning')
			return redirect(url_for('assignments.view_assignments'))
	else:
		peer_review_form_id = Assignment.query.get(assignment_id).peer_review_form_id	
		form_data = PeerReviewForm.query.get(peer_review_form_id).serialised_form_data
		form_loader = app.assignments.formbuilder.formLoader(form_data, (url_for('assignments.create_peer_review', assignment_id=assignment_id)))
		render_form = form_loader.render_form()
		return render_template('assignments/form_builder_render.html', title='Submit peer review', render_form=render_form)
		

# Display an empty review feedback form
@bp.route("/create_teacher_review/<upload_id>", methods=['GET', 'POST'])
@login_required
def create_teacher_review(upload_id):
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		peer_review_form_id = Assignment.query.join(
			Upload, Upload.assignment_id == Assignment.id).filter(
			Upload.id == upload_id).first().peer_review_form_id
		form_data = PeerReviewForm.query.get(peer_review_form_id).serialised_form_data
		form_loader = app.assignments.formbuilder.formLoader(form_data, (url_for('assignments.create_teacher_review', upload_id=upload_id)))
		render_form = form_loader.render_form()
		
		# Get assignment and user details
		assignment_id = Upload.query.get(upload_id).assignment_id
		assignment_info = Assignment.query.get(assignment_id)
		user_info = User.query.get(Upload.query.get(upload_id).user_id)
		class_info = Turma.query.get(assignment_info.target_turma_id)
		
		if request.method == 'POST':
			form_contents = json.dumps(request.form)
			update_comment = app.assignments.models.add_teacher_comment_to_upload(form_contents, upload_id)
			flash('Teacher review submitted succesfully!', 'success')
			# For this assignment (class), get a list of uploads that haven't been commented on by current_user.id
			not_yet_graded_uploads = []
			uploads = Upload.query.join(User, Upload.user_id == User.id).filter(
				Upload.assignment_id == assignment_id).order_by(
				User.student_number.asc()).all()
			for upload in uploads:
				if Comment.query.filter(Comment.file_id == upload.id).filter(Comment.user_id ==current_user.id).first() is None:
					# There is an assignment that hasn't been graded, redirect to the grading page
					return redirect(url_for('assignments.create_teacher_review', upload_id = upload.id))
			# No more assignments to be graded, return to assignment detail page
			return redirect(url_for('assignments.view_assignment_details', assignment_id = assignment_id))
		return render_template('files/peer_review_form.html',
								title='Submit a teacher review',
								assignment_info = Assignment.query.get(assignment_id),
								user_info = User.query.get(Upload.query.get(upload_id).user_id),
								class_info = class_info,
								form=render_form)
	abort (403)


# Let a receiver or author view a completed peer review
@bp.route("/view_peer_review/<comment_id>")
@login_required
def view_peer_review(comment_id):
	if current_user.id is models.get_file_owner_id (
		Comment.query.get(comment_id).file_id) or current_user.id is app.assignments.models.get_comment_author_id_from_comment(
		comment_id) or app.models.is_admin(current_user.username):
	
		peer_review_form_id = db.session.query(Assignment).join(
			Comment, Assignment.id==Comment.assignment_id).filter(
			Comment.id==comment_id).first().peer_review_form_id
		
		form_contents = json.loads(Comment.query.get(comment_id).comment)
		
		if current_user.id is app.assignments.models.get_comment_author_id_from_comment(
		comment_id):
			flash('You can not edit this peer review as it has already been submitted.', 'info')
			
		form_data = PeerReviewForm.query.get(peer_review_form_id).serialised_form_data

		form_loader = app.assignments.formbuilder.formLoader(form_data,
															 (url_for('assignments.view_assignments')),
															 submit_label = 'Return',
															 data_array = form_contents)
		render_form = form_loader.render_form()
		return render_template('assignments/form_builder_render.html',
							   render_form=render_form, title = 'Peer review')
		
	else: abort (403)
	
############# Peer review forms routes


@bp.route("/form/builder")
def form_builder():
	return render_template('assignments/form_builder_index.html')

@bp.route('/form/save', methods=['POST'])
def save():
	if request.method == 'POST':
		form_data = request.form.get('formData')
		if form_data == 'None':
			return 'Error processing request'
		else:
			json_string = r'''{}'''.format(form_data)
			json_data = json.loads(json_string)
			
			peer_review_form = PeerReviewForm()
			peer_review_form.title = json_data['title']
			peer_review_form.description = json_data['description']
			peer_review_form.serialised_form_data = json.dumps(json_data)
			db.session.add(peer_review_form)
			db.session.commit()
		session['form_data'] = form_data
		print(form_data)
	return 'True'

@bp.route('/form/render')
@bp.route('/form/render/<form_id>')
def render(form_id = False):
	if form_id:
		form_data = PeerReviewForm.query.get(form_id).serialised_form_data
	elif not session['form_data']:
		redirect(url_for('main.index'))
	else:
		form_data = session['form_data']
		session['form_data'] = None

	form_loader = app.assignments.formbuilder.formLoader(form_data, (url_for('assignments.submit')))
	render_form = form_loader.render_form()
	print (render_form)
	return render_template('assignments/form_builder_render.html', render_form=render_form)

@bp.route('/form/delete/<form_id>')
def delete_peer_review_form(form_id):
	#!# Check if form is in use by any assignments?
	
	PeerReviewForm.query.filter(PeerReviewForm.id == form_id).delete()
	db.session.commit()
	flash ('Form deleted successfully.', 'success')
	return (redirect(url_for('assignments.peer_review_form_admin')))

@bp.route('/form/builder/submit', methods=['POST'])
def submit():
	if request.method == 'POST':
		form = json.dumps(request.form)

		return form

@bp.route("/add_peer_review_form", methods=['GET', 'POST'])
@login_required
def add_peer_review_form():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		return (redirect(url_for('assignments.form_builder')))
	abort(403)

# Admin page to view classes
@bp.route("/peer_review_form_admin")
@login_required
def peer_review_form_admin():
	if current_user.is_authenticated and app.models.is_admin(current_user.username):
		peer_review_forms = PeerReviewForm.query.all()
		return render_template('assignments/manage_peer_review_forms.html', peer_review_forms=peer_review_forms)
	abort (403)

	