from flask import Flask, render_template, request, Response, make_response, send_file, redirect, url_for, send_from_directory, flash, abort
from flask_httpauth import HTTPBasicAuth
from random import randint
from werkzeug import secure_filename
import glob, os

# Set app variables
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_LOCATION = 'static/uploads'
UPLOAD_FOLDER = os.path.join(APP_ROOT, UPLOAD_LOCATION)
ALLOWED_EXTENSIONS = set(['txt', 'zip', 'pdf', 'doc', 'docx', 'pages'])

# Create class and load variables
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# App security for stageing server
import config
app.secret_key = config.app_secret_key
auth = HTTPBasicAuth()

users = {
    "john": "hello",
    "susan": "bye"
}

@auth.get_password
def get_pw(username):
    if username in users:
        return users.get(username)
    return None

# Check filename and extension permissibility
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Return the number of files in the upload folder
def getNumberOfFiles():
	return (len (os.listdir(app.config['UPLOAD_FOLDER'])) - 1 )



# Choose a random file from uploads folder and send it out for download
@app.route('/download-peer-file', methods = ['GET', 'POST'])
def downloadRandomFile():	
   uploadedFiles = (os.listdir(app.config['UPLOAD_FOLDER']))
   numberOfFiles = int (getNumberOfFiles())
   randomNumber = (randint(0,numberOfFiles - 1))
   randomFile = os.path.join (UPLOAD_LOCATION, uploadedFiles[randomNumber])
   return send_file(randomFile, as_attachment=True)

# Send out specific file for download
def downloadFile(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Sends out a file for download
# Input: filename (must be in upload folder)
@app.route('/uploaded/<filename>')
def uploaded_file(filename):
    #return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
	return render_template ('fileUploaded.html')
   

# Main entrance to the app
@app.route('/', methods=['GET', 'POST'])
@auth.login_required
def upload_file():
	# If the form has been filled out and posted:
	if request.method == 'POST':
		# Check if the post request has the file part
		if 'file' not in request.files:
			flash('No file uploaded.')
			return redirect(request.url)
		file = request.files['file']
		if file.filename == '':
			flash('Please rename the file.')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('uploaded_file',filename=filename))
	else:
		return render_template('fileUpload.html')

# Access file stats
@app.route("/fileStats")
@auth.login_required
def fileStats():
   printOutput = 'There are ' + str(getNumberOfFiles()) +' files in the folder: <br/>'
   uploadedFiles = (glob.glob(app.config['UPLOAD_FOLDER'] + '/*'))
   for files in uploadedFiles:
      printOutput = printOutput + str(files) + ", <br/>"
   return str(printOutput)


if __name__ == '__main__':
   app.run()