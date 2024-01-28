from flask import Flask, redirect, request, render_template
app = Flask(__name__)

@app.route('/') 
def index():
    # user_agent = request.headers.get('User-Agent')
    # return f'<h1>Your browser is {user_agent}</h1>'
	# return '<h1>Bad Request</h1>', 400
	# return redirect('http://www.example.com')
	return render_template('index.html')

@app.route('/user/<name>')
def user(name):
	return render_template('user.html', name = name)
