# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from models import visits_collection
from plate_ocr import extract_plate_from_base64

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "Live", "database": "AWS MongoDB Atlas Connected"}), 200

@app.route("/api/visits", methods=["POST"])
def create_visit():
    try:
        data = request.json or {}
        
        # 1. Get form details
        form_vehicle_number = data.get("vehicleNumber", "").upper().replace(" ", "")
        image_b64 = data.get("vehicleNoPhoto")
        
        ocr_plate = ""
        plate_match = False

        # 2. Process the camera image through OCR
        if image_b64:
            ocr_result = extract_plate_from_base64(image_b64)
            ocr_plate = ocr_result.get("plate", "")
            
            # 3. Match the detected text against the registered form number
            if ocr_plate and form_vehicle_number:
                # Basic string match logic (can be adjusted for fuzzy matching)
                if form_vehicle_number in ocr_plate or ocr_plate in form_vehicle_number:
                    plate_match = True

        # 4. Prepare data for AWS MongoDB
        data["ocr_plate_detected"] = ocr_plate
        data["plate_match_success"] = plate_match
        data["status"] = "approved" if plate_match else "pending_review"
        data["submittedAt"] = datetime.utcnow()

        result = visits_collection.insert_one(data)
        
        return jsonify({
            "message": "Gate Pass Processed",
            "id": str(result.inserted_id),
            "detected_plate": ocr_plate,
            "match": plate_match
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/visits", methods=["GET"])
def get_visits():
    try:
        cursor = visits_collection.find().sort("submittedAt", -1)
        visits = [{**doc, "_id": str(doc["_id"])} for doc in cursor]
        return jsonify(visits), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ==========================================================
# 4. PUT ROUTE (To update Approve/Reject status)
# ==========================================================
@app.route("/api/visits/<receipt_id>/status", methods=["PUT"])
def update_visit_status(receipt_id):
    try:
        data = request.json
        new_status = data.get("status")
        
        # Update the document matching the receiptId in AWS MongoDB
        result = visits_collection.update_one(
            {"receiptId": receipt_id},
            {"$set": {"status": new_status}}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Receipt not found"}), 404
            
        return jsonify({"message": f"Status updated to {new_status}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==========================================================
# 5. DELETE ROUTE (To permanently delete a gate pass)
# ==========================================================
@app.route("/api/visits/<receipt_id>", methods=["DELETE"])
def delete_visit(receipt_id):
    try:
        # Delete the document from AWS MongoDB
        result = visits_collection.delete_one({"receiptId": receipt_id})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Receipt not found"}), 404
            
        return jsonify({"message": "Gate pass deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)