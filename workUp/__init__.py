from flask import Flask, render_template, request, Response, make_response, send_file, redirect, url_for, send_from_directory, flash
from random import randint
from werkzeug import secure_filename
import glob, os

# Set app variables
UPLOAD_FOLDER = 'uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'zip', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])

# Create class and load variables
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.secret_key = 'ignitors0gitanas*vapours3'

### Helper functions ###
# Check filename and extension permissibility
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def getNumberOfFiles():
	return len (glob.glob("uploads/*"))
#########################

# Choose a random file from uploads folder and send it out for download
def selectRandomFile():	
   uploadedFiles = (glob.glob(app.config['UPLOAD_FOLDER'] + '/*'))
   numberOfFiles = int (getNumberOfFiles())
   randomNumber = (randint(0,numberOfFiles - 1))

   randomFile = uploadedFiles[randomNumber]
   return send_file(randomFile, as_attachment=True)

@app.route('/listdir')
def printCDFiles():
	return str(app.root_path)


# Sends out a file for download
# Input: filename (must be in upload folder)
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
   

@app.route('/', methods=['GET', 'POST'])
def upload_file():
	# If the form has been filled out and posted:
	if request.method == 'POST':
		# check if the post request has the file part
		if 'file' not in request.files:
			flash('No file part')
			return redirect(request.url)
		file = request.files['file']
		# if user does not select file, browser also submit a empty part without filename
		if file.filename == '':
			flash('No file')
			return redirect(request.url)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('uploaded_file',filename=filename))
	else:
		return render_template('fileUpload.html')
        
@app.route("/fileStats")
def fileStats():
   printOutput = 'There are ' + str(getNumberOfFiles()) +' files in the folder: <br/>'
   
   uploadedFiles = (glob.glob(app.config['UPLOAD_FOLDER'] + '/*'))
   
   for files in uploadedFiles:
      printOutput = printOutput + str(files) + ", <br/>"
      
   return str(printOutput)


	


if __name__ == '__main__':
   app.run(debug = True)