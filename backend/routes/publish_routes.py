"""发布中心 API 路由。"""

from flask import Blueprint, jsonify, request

from backend.auth import require_user
from backend.services.content import get_content_service
from backend.services.history import get_history_service
from backend.services.publish import get_publish_service


def create_publish_blueprint():
    publish_bp = Blueprint("publish", __name__)

    @publish_bp.route("/publish/accounts", methods=["GET"])
    @require_user()
    def list_accounts(current_user):
        platform = request.args.get("platform")
        service = get_publish_service()
        return jsonify({
            "success": True,
            "accounts": service.list_accounts(platform=platform, current_user=current_user),
        }), 200

    @publish_bp.route("/publish/accounts", methods=["POST"])
    @require_user()
    def create_account(current_user):
        try:
            data = request.get_json(silent=True) or {}
            account_id = get_publish_service().create_account(
                name=(data.get("name") or "").strip(),
                platform=data.get("platform") or "xhs",
                current_user=current_user,
            )
            return jsonify({"success": True, "account_id": account_id}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @publish_bp.route("/publish/accounts/<account_id>", methods=["DELETE"])
    @require_user()
    def delete_account(current_user, account_id):
        success = get_publish_service().delete_account(account_id, current_user=current_user)
        if not success:
            return jsonify({"success": False, "error": "发布账号不存在"}), 404
        return jsonify({"success": True}), 200

    @publish_bp.route("/publish/accounts/<account_id>/login", methods=["POST"])
    @require_user()
    def open_login(current_user, account_id):
        try:
            result = get_publish_service().open_login(account_id, current_user=current_user)
            return jsonify(result), 200 if result.get("success") else 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @publish_bp.route("/publish/drafts", methods=["POST"])
    @require_user()
    def create_draft(current_user):
        try:
            data = request.get_json(silent=True) or {}
            creation_id = data.get("creation_id") or ""
            if not get_history_service().get_record(creation_id, current_user=current_user):
                return jsonify({"success": False, "error": "无权发布该作品或作品不存在"}), 403
            draft_id = get_publish_service().create_draft(
                creation_id=creation_id,
                account_id=data.get("account_id") or "",
                title=(data.get("title") or "").strip(),
                body=(data.get("body") or "").strip(),
                tags=data.get("tags") or [],
                page_indexes=data.get("page_indexes"),
                current_user=current_user,
            )
            return jsonify({"success": True, "draft_id": draft_id}), 200
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @publish_bp.route("/publish/drafts/<draft_id>/run", methods=["POST"])
    @require_user()
    def run_draft(current_user, draft_id):
        try:
            result = get_publish_service().run_draft(draft_id, current_user=current_user)
            return jsonify(result), 200 if result.get("success") else 400
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 400

    @publish_bp.route("/publish/jobs/<job_id>", methods=["GET"])
    @require_user()
    def get_job(current_user, job_id):
        job = get_publish_service().get_job(job_id, current_user=current_user)
        if not job:
            return jsonify({"success": False, "error": "发布任务不存在"}), 404
        return jsonify({"success": True, "job": job}), 200

    @publish_bp.route("/publish/jobs", methods=["GET"])
    @require_user()
    def list_jobs(current_user):
        try:
            limit = int(request.args.get("limit") or 50)
        except ValueError:
            limit = 50
        return jsonify({
            "success": True,
            "jobs": get_publish_service().list_jobs(limit=limit, current_user=current_user),
        }), 200

    @publish_bp.route("/publish/jobs/<job_id>/cancel", methods=["POST"])
    @require_user()
    def cancel_job(current_user, job_id):
        result = get_publish_service().cancel_job(job_id, current_user=current_user)
        return jsonify(result), 200 if result.get("success") else 400

    @publish_bp.route("/publish/tags/suggest", methods=["POST"])
    @require_user()
    def suggest_tags(_current_user):
        try:
            data = request.get_json(silent=True) or {}
            title = (data.get("title") or "").strip()
            body = (data.get("body") or "").strip()
            if not title or not body:
                return jsonify({"success": False, "error": "标题和正文不能为空"}), 400
            result = get_content_service().generate_tags(title, body)
            return jsonify(result), 200 if result.get("success") else 500
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    return publish_bp
