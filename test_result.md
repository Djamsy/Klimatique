#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Problème avec gestion des risques IA bloquée à 'modéré' en vigilance verte + ajout intégration Facebook/Twitter pour posts automatiques évolution météo"

backend:
  - task: "Résolution problème risques IA bloqués à 'modéré'"
    implemented: true
    working: true
    file: "/app/backend/ai_models/cyclone_damage_predictor.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Analyse détaillée effectuée - système fonctionne correctement. Risques peuvent bien être 'faible' en vigilance verte. Tests confirmés sur 3 communes."
        -working: true
        -agent: "testing"
        -comment: "Tests réussis sur Pointe-à-Pitre, Basse-Terre, Sainte-Anne. Système peut retourner tous niveaux de risque (faible, modéré, élevé, critique). Architecture solide."

  - task: "Service réseaux sociaux Facebook/Twitter"
    implemented: true
    working: true
    file: "/app/backend/services/social_media_service.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Service complet créé avec support Twitter API v2 et Facebook Graph API. Formatage posts météo, stockage identifiants, statistiques."
        -working: true
        -agent: "testing"
        -comment: "Service initialisé correctement. Test connexions OK, formatage posts météo fonctionnel, stockage credentials opérationnel. Gestion erreurs sans credentials appropriée."

  - task: "Planificateur posts automatiques"  
    implemented: true
    working: true
    file: "/app/backend/services/social_post_scheduler.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Scheduler avec APScheduler créé. Posts matinaux/soir, alertes vigilance, posts critiques. Tâches CRON configurées."
        -working: true
        -agent: "testing"
        -comment: "Scheduler opérationnel. Status endpoint fonctionnel, programmation/annulation posts OK. Jobs actifs détectés. Prêt pour activation."

  - task: "Endpoints API réseaux sociaux"
    implemented: true  
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "9 endpoints ajoutés: credentials, post, schedule, stats, scheduler control, test connections. Intégration avec données météo/IA."
        -working: true
        -agent: "testing"
        -comment: "Tous endpoints testés avec succès: /social/test-connections, /social/scheduler/status, /social/stats, /social/post, /social/schedule, /social/credentials. Intégration météo fonctionnelle."

  - task: "Modèles Pydantic réseaux sociaux"
    implemented: true
    working: true
    file: "/app/backend/models.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Modèles SocialPlatform, SocialCredentialsRequest, SocialPostRequest, ScheduledPostRequest et réponses ajoutés."
        -working: true
        -agent: "testing"
        -comment: "Modèles Pydantic validés et fonctionnels. SocialStatsResponse corrigé (suppression champs incorrects). Validation données OK."

  - task: "Dépendances réseaux sociaux"
    implemented: true
    working: true
    file: "/app/backend/requirements.txt"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Ajout apscheduler, tweepy, facebook-sdk dans requirements.txt et installation réussie."
        -working: true
        -agent: "testing"
        -comment: "Dépendances installées et fonctionnelles. Services s'initialisent correctement avec avertissements appropriés pour credentials manquants."

frontend:

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 3
  run_ui: false

test_plan:
  current_focus:
    - "Service réseaux sociaux Facebook/Twitter"
    - "Planificateur posts automatiques"
    - "Endpoints API réseaux sociaux"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: "Intégration Facebook/Twitter complète implémentée. Service de posts automatiques avec scheduler, 9 endpoints API, formatage posts météo avec données IA/vigilance. Problème risques IA analysé - système fonctionne correctement. Prêt pour tests backend."
    -agent: "testing"
    -message: "Tests backend réseaux sociaux terminés avec succès (12/12 tests passés). Tous endpoints fonctionnels, modèles Pydantic corrigés, services initialisés. Architecture solide et prête pour vraies clés API. Problème SocialStatsResponse résolu, WeatherCache modèle corrigé."