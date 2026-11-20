from backend.route.assignments import bp as assignments_bp
from backend.route.threats import bp as threats_bp
from backend.route.lab71_routes import bp as lab71_bp
from backend.route.lab72_routes import bp as lab72_bp
from backend.route.monitoring import bp as monitoring_bp
from backend.route.lab10_12_routes import bp as lab10_12_bp


from backend.route.ai import bp as ai_bp
from backend.route.lab_operations import bp as lab_operations_bp

def register_routes(app):
    for bp in (threats_bp, lab71_bp, lab72_bp, monitoring_bp, assignments_bp, lab10_12_bp, ai_bp, lab_operations_bp):
        app.register_blueprint(bp, url_prefix="/api")
