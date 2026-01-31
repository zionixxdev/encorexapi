from flask import Flask, jsonify

app = Flask(__name__)

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "error": "kya re bhenkelode",
        "status": 404
    }), 404

@app.route("/")
def home():
    return "toremayekochodo"
  
