#Environment setup Scripts:
#Step 1: check python version
#        Using python3: python3 --version
#Step 2: Set Up the Virtual Environment
#        use python3:
#        python3 -m venv venv
#
#        Now activate the virtual environment:
#        source venv/bin/activate
#
#        You should see something like (venv) appear in your terminal prompt.
#        If activation fails, try:
#        . venv/bin/activate
#
#        To deactivate the virtual environment later, just type:
#        deactivate
#
#Step 3: Install Required Packages
#        Now that your virtual environment is active, install the necessary Python libraries:
#        pip install spacy nltk pandas
#Step 4: Verify Everything Works
#        Run:
#        python3 -m spacy download en_core_web_md
#             This downloads the necessary NLP model for spaCy.
#       
#        Check installed packages:
#        pip list

import spacy
import re
from nltk.tokenize import sent_tokenize
import pandas as pd
from collections import Counter
import nltk
from nltk.corpus import stopwords
import ssl

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('stopwords')

class RequirementsExtractor:
    def __init__(self):
        # Load SpaCy model
        self.nlp = spacy.load("en_core_web_md")
        self.stop_words = set(stopwords.words('english'))
        
    def extract_requirements(self, system_description):
        # Preprocess text
        sentences = self.preprocess_text(system_description)
        
        # Extract features
        features = self.extract_features(sentences)
        
        # Identify potential requirements
        potential_reqs = self.identify_potential_requirements(features)
        
        # Formulate requirements
        formulated_reqs = self.formulate_requirements(potential_reqs)
        
        # Refine requirements
        refined_reqs = self.refine_requirements(formulated_reqs)
        
        # Classify requirements
        classified_reqs = self.classify_requirements(refined_reqs)
        
        return classified_reqs
    
    def preprocess_text(self, text):
        # Clean text
        text = re.sub(r'\s+', ' ', text)
        
        # Split into sentences
        sentences = sent_tokenize(text)
        
        # Filter out short or irrelevant sentences
        sentences = [s for s in sentences if len(s.split()) > 5]
        
        return sentences
    
    def extract_features(self, sentences):
        features = []
        
        for sentence in sentences:
            doc = self.nlp(sentence)
            
            # Extract various linguistic features
            verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
            action_verbs = [v for v in verbs if v in ["allow", "enable", "provide", "support", "manage", "monitor", "check", "view", "book", "pay", "receive", "create", "track", "generate"]]
            
            nouns = [token.text for token in doc if token.pos_ == "NOUN"]
            entities = [ent.text for ent in doc.ents]
            
            # Extract subject-verb-object patterns
            svo_patterns = []
            for chunk in doc.noun_chunks:
                if chunk.root.dep_ == "nsubj" and chunk.root.head.pos_ == "VERB":
                    verb = chunk.root.head.lemma_
                    subject = chunk.text
                    
                    # Try to find objects
                    for token in doc:
                        if token.head == chunk.root.head and token.dep_ in ["dobj", "pobj"]:
                            obj = token.text
                            svo_patterns.append((subject, verb, obj))
            
            # Extract modal verbs (should, must, will) which often indicate requirements
            modals = [token.text for token in doc if token.dep_ == "aux" and token.text.lower() in
                      ["should", "must", "will", "can", "could"]]
            
            features.append({
                "sentence": sentence,
                "verbs": verbs,
                "action_verbs": action_verbs,
                "nouns": nouns,
                "entities": entities,
                "svo_patterns": svo_patterns,
                "modals": modals,
                "doc": doc
            })
        
        return features
    
    def identify_potential_requirements(self, features):
        potential_reqs = []
        
        for feature in features:
            score = 0
            
            # Score based on action verbs
            if feature["action_verbs"]:
                score += len(feature["action_verbs"]) * 2
                
            # Score based on modal verbs
            if feature["modals"]:
                score += len(feature["modals"]) * 3
                
            # Score based on subject-verb-object patterns
            if feature["svo_patterns"]:
                score += len(feature["svo_patterns"]) * 2
                
            # Keywords that often indicate requirements
            requirement_keywords = ["need", "require", "must", "should", "allow", "enable", "access", "view", "book", "reserve"]
            if any(keyword in feature["sentence"].lower() for keyword in requirement_keywords):
                score += 3
            
            # Check for system components mentioned
            system_components = ["machine", "payment", "reservation", "notification", "camera", "account", "feedback", "review"]
            if any(component in feature["sentence"].lower() for component in system_components):
                score += 2
                
            # Check for user roles
            user_roles = ["customer", "client", "user", "administrator", "owner"]
            if any(role in feature["sentence"].lower() for role in user_roles):
                score += 2
                
            # Store the potential requirement with its score
            feature["req_score"] = score
            potential_reqs.append(feature)
        
        # Sort by score and filter
        potential_reqs.sort(key=lambda x: x["req_score"], reverse=True)
        return [req for req in potential_reqs if req["req_score"] > 3]
    
    def formulate_requirements(self, potential_reqs):
        formulated_reqs = []
        
        for req in potential_reqs:
            doc = req["doc"]
            
            # Try to identify the actor (subject)
            actors = []
            for chunk in doc.noun_chunks:
                if chunk.root.dep_ == "nsubj":
                    actors.append(chunk.text)
            
            # Identify primary stakeholder
            if any(actor.lower() in ["customer", "client", "user"] for actor in actors if actor):
                primary_actor = "The customer"
            elif any(actor.lower() in ["administrator", "admin", "owner"] for actor in actors if actor):
                primary_actor = "The administrator"
            else:
                primary_actor = "The system"
            
            # Try to identify the action
            actions = req["action_verbs"] if req["action_verbs"] else req["verbs"]
            action = actions[0] if actions else "support"
            
            # Try to identify the object
            objects = []
            for chunk in doc.noun_chunks:
                if chunk.root.dep_ in ["dobj", "pobj"]:
                    objects.append(chunk.text)
            
            # Formulate the requirement
            if actors and actions and objects:
                requirement = f"{primary_actor} shall {action} {objects[0]}"
            else:
                # Fall back to template based on the sentence
                requirement = f"{primary_actor} shall {action} {req['sentence'].lower()}"
            
            # Clean up the requirement
            requirement = requirement.replace("  ", " ").strip()
            
            # Add more context if available from the original sentence
            for chunk in doc.noun_chunks:
                if chunk.root.dep_ in ["pobj"] and chunk.text not in requirement:
                    if not requirement.endswith('.'):
                        requirement += f" for {chunk.text}"
                        
            formulated_reqs.append(requirement)
        
        return formulated_reqs
    
    def refine_requirements(self, formulated_reqs):
        # Remove duplicates
        unique_reqs = []
        seen = set()
        
        for req in formulated_reqs:
            # Create a simplified version for comparison
            simple_req = re.sub(r'[^a-zA-Z0-9]', '', req.lower())
            
            # Check if we've seen this requirement
            if simple_req not in seen and len(req.split()) > 4:
                seen.add(simple_req)
                unique_reqs.append(req)
        
        # Ensure consistent formatting
        refined_reqs = []
        for req in unique_reqs:
            # Make sure requirements start with standard phrases
            if not any(req.lower().startswith(prefix) for prefix in ["the system shall", "the customer should", "the administrator should"]):
                req = f"The system shall {req}"
            
            # Ensure requirements end with a period
            if not req.endswith('.'):
                req += '.'
                
            # Fix common issues
            req = req.replace(" should be able to be able to ", " should be able to ")
            req = req.replace(" should should ", " should ")
            req = req.replace(" shall shall ", " shall ")
            
            refined_reqs.append(req)
        
        return refined_reqs
    
    def classify_requirements(self, refined_reqs):
        classifications = []
        
        for req in refined_reqs:
            doc = self.nlp(req)
            
            # Identify stakeholder
            stakeholder = "System"
            if "customer" in req.lower() or "client" in req.lower() or "user" in req.lower():
                stakeholder = "Customer"
            elif "administrator" in req.lower() or "admin" in req.lower() or "owner" in req.lower():
                stakeholder = "Administrator"
            
            # Identify requirement type
            req_type = "Functional"
            non_functional_keywords = ["performance", "security", "reliability", "usability", "maintainability"]
            if any(keyword in req.lower() for keyword in non_functional_keywords):
                req_type = "Non-functional"
            
            # Identify feature category
            categories = []
            category_keywords = {
                "Washing/Drying": ["machine", "washer", "dryer", "washing", "drying"],
                "Security": ["security", "camera", "monitor", "surveillance"],
                "Scheduling": ["schedule", "booking", "reservation", "book", "reserve"],
                "Payment": ["payment", "pay", "coin", "card", "credit", "debit"],
                "Reporting": ["report", "record", "track", "log"],
                "Communication": ["communicate", "notification", "alert", "message"],
                "Feedback": ["feedback", "review", "comment", "rating"]
            }
            
            for category, keywords in category_keywords.items():
                if any(keyword in req.lower() for keyword in keywords):
                    categories.append(category)
            
            if not categories:
                categories = ["General"]
            
            classifications.append({
                "requirement": req,
                "stakeholder": stakeholder,
                "type": req_type,
                "categories": categories
            })
        
        return classifications

    def extract_and_format(self, system_description):
        """
        Extract and format requirements from system description into a structured format
        """
        classified_reqs = self.extract_requirements(system_description)
        
        # Group by stakeholder
        customer_reqs = [req for req in classified_reqs if req["stakeholder"] == "Customer"]
        admin_reqs = [req for req in classified_reqs if req["stakeholder"] == "Administrator"]
        system_reqs = [req for req in classified_reqs if req["stakeholder"] == "System"]
        
        formatted_reqs = []
        
        # Format customer requirements
        for req in customer_reqs:
            formatted_reqs.append(req["requirement"])
            
        # Format admin requirements
        for req in admin_reqs:
            formatted_reqs.append(req["requirement"])
            
        # Format system requirements
        for req in system_reqs:
            formatted_reqs.append(req["requirement"])
            
        return formatted_reqs


# Example usage
if __name__ == "__main__":
    extractor = RequirementsExtractor()
    
    # Example system description
    system_description = """
A laundromat provides self-service washing and drying machines for customers. Customers can walk in and use available machines or reserve a machine in advance through an online booking system. Each washing machine and dryer has a unique identifier. Customers must select a machine, choose a wash or dry cycle, and make a payment before starting the machine. Payments can be made using coins, a prepaid card, or an online payment system.

Once the machine is started, the system displays the remaining time for the cycle. Customers can check the status of their machine using a mobile app or a kiosk at the laundromat. If a machine finishes and the laundry is not removed within 10 minutes, the system sends a reminder notification to the customer. If the machine is still occupied after 30 minutes, staff may move the laundry to a designated area.

The laundromat also offers a drop-off service where customers can leave their laundry with an attendant, who will wash, dry, and fold the clothes. The system tracks drop-off orders, assigns them to available attendants, and notifies customers when their laundry is ready for pickup.

The laundromat system also maintains a maintenance log for each machine, automatically flagging machines that require servicing based on error reports or usage counts. Staff can update the status of machines and schedule repairs.
    """
    
    # Extract requirements
    requirements = extractor.extract_and_format(system_description)
    
    # Print extracted requirements
    for i, req in enumerate(requirements, 1):
        print(f"{i}. {req}")
