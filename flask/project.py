import json
import uuid
import time
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response
from bson.json_util import ObjectId,dumps
from array import *
import collections
from collections import defaultdict


#Mongo
client = MongoClient('mongodb://localhost:27017/')
#Database
db = client['DSPharmacy']
#Collections
users = db['Users']
products = db['Products']



class MyEncoder(json.JSONEncoder): 
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)

#Flask start
app = Flask(__name__)
app.json_encoder = MyEncoder
app.config['JSON_SORT_KEYS'] =True



#Users session
users_sessions = {}

#User session creation
def create_session(email):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = (email, time.time())
    return user_uuid


def is_session_valid(user_uuid):
    return user_uuid in users_sessions



#User Creation
@app.route('/createUser', methods=['POST'])
def create_user():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "email" in data or not "name" in data or not "password" in data or not "ssn" in data or not "category" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")
    s=str(data['ssn'])
    global split_string
    split_string = [s[i:i+2] for i in range(0,len(s),2)]
    if int(split_string[0]) > 31 or int(split_string[1]) > 12 :
        return Response("Wrong AMKA numbers.", status=500, mimetype="application/json")

    if users.find({"email": data["email"]}).count() == 0:
            user = {"email": data['email'],"name": data['name'], "password": data['password'], "ssn": data['ssn'],"category":"User"}
            users.insert_one(user)
            # Μήνυμα επιτυχίας
            return Response(data['name'] + " was added to the MongoDB", mimetype='application/json',status=200)  # ΠΡΟΣΘΗΚΗ STATUS

        # Διαφορετικά, αν υπάρχει ήδη κάποιος χρήστης με αυτό το email.
    else:
            # Μήνυμα λάθους (Υπάρχει ήδη κάποιος χρήστης με αυτό το email)
            return Response("A user with the given email already exists", mimetype='application/json',status=400)  # ΠΡΟΣΘΗΚΗ STATUS

#User login
@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data or not "password" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    # Έλεγχος δεδομένων username / password
    # Αν η αυθεντικοποίηση είναι επιτυχής. 
    if users.find({'$and':[{"email":data["email"]},{"password":data["password"]},{ "ssn": data['ssn']},{"category":"User"} ]}).count() != 0 :
        global user_email
        user_email = data['email']
        user_uuid=create_session(users.find({"email":data["email"]}))
        res = {"uuid": user_uuid, "email": data['email']}
        return Response(json.dumps(res), mimetype='application/json',status=200) # ΠΡΟΣΘΗΚΗ STATUS

    # Διαφορετικά, αν η αυθεντικοποίηση είναι ανεπιτυχής.
    else:
        # Μήνυμα λάθους (Λάθος username ή password)
        return Response("Wrong email or password.",mimetype='application/json',status=400,) # ΠΡΟΣΘΗΚΗ STATUS



            
@app.route('/getProduct', methods=['GET'])   
def get_product():
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    uuid = request.headers.get('authorization')
    if is_session_valid(uuid) is False:
        return Response("User has not been authenticated",status=401,mimetype="application/json")
    else:
        if "name" in data:
            product = products.find({"name":data["name"]})
            if product != None :
                Products = []
                for i in product:
                    Products.append(i)
                return jsonify(Products)
            if product == None :
                return Response("No product found with that name",status=400,mimetype='application/json')
        #Search by category
        if "category" in data: 
            product = products.find({"category":data["category"]})
            if product != None :
                Products = []
                for i in product:
                    Products.append(i)
                return jsonify(Products)
            if product == None :
                return Response("No product found by this category",status=400,mimetype='application/json')
        # Search by ID
        if "_id" in data:
            product = products.find_one({"_id": ObjectId(data["_id"])})
            if product != None :
                product = {'name':product["name"], 'description':product["description"], 'price':product["price"], 'category':product["category"], '_id':str(product["_id"])}
                return Response(json.dumps(product), status=200, mimetype='application/json')
            if product == None : 
                return Response("No product found by that ID",status=400,mimetype="application/json")   
        if "name" in data and "_id" in data and "category" in data :
            return Response(json.dumps("Plase use only one option: name or _id or category"),status=400,mimetype="application/json")  



global basket,price_list, new_price_end, new_price_list, cost
new_price_list = []
new_price_end = []
price_list = []
basket = []

#Prosthiki sto kalathi
@app.route('/addBasket/<int:quantity>', methods=['PUT']) 
def add_basket(quantity):

    def totalPrice(price):
            for k in basket:
                price_list.append(price)
                if len(price_list) > 1:
                    cost = sum(price_list)
                    return cost


                if len(price_list) == 1 :
                    cost =price
                    return cost
    
    
    uuid = request.headers.get('authorization')


    if is_session_valid(uuid) is False:
        return Response("User has not been authenticated",status=401,mimetype="application/json")
    else:
        id=request.args.get("id")
        product=products.find_one({"_id":ObjectId(id)})
        
        if quantity > int(product["stock"]):
                return Response('Stock is not enough,please enter lower number.' ,status=500,mimetype='application/json')
        if product != None :
            price = int(product["price"])*quantity
            
            product = {"_id":product["_id"], "Total cost of product":price, "name": product["name"], "description":product["description"], "category":product["category"], "Quantity of Product":int(quantity)}
            basket.append(product)
            if basket != None:
                global price_end,whole_cost 
                price_end= totalPrice(price)
                whole_cost = price_end
                Products = []
                for i in basket:
                     Products.append(i)
                return jsonify("Products Successfully added to cart.",Products,"Total cost is:",price_end,"€")
            else:
                    return Response(json.dumps("Product doesn't exist!"),status=500,mimetype="application/json")
        else :
            return Response(json.dumps("Id doesn't match to product"),status=500,mimetype="application/json")



#Emfanisi kalathiou

@app.route('/getBasket', methods=['GET'])
def get_basket():
    uuid = request.headers.get('Authorization')
    if is_session_valid(uuid)  == False :
        return Response("User was not authenticated ", status=401, mimetype='application/json')
    else:
        if basket != None:
            global whole_cost
            return jsonify('Your cart:',basket,'Your receipt:',whole_cost,"€")     
        else:
            return Response(json.dumps('Shopping cart is empty!'),status=500,mimetype="application/json")



#Diagrafi apo to kalathi
@app.route('/deleteFromBasket', methods=['DELETE'])
def delete_from_basket():
    uuid = request.headers.get('Authorization')
    if is_session_valid(uuid) == False :
        return Response("User was not authenticated ", status=401, mimetype='application/json')
    else:
            id=request.args.get("id")
            item=id
           
            global price_end
           
           
            global basket_finished
            if len(basket) != 0 :
                for k in range(len(basket)) :
                    if str(basket[k]["_id"]) is str(item):
                        global new_price_end
                        new_price_end = price_end - basket[k]["Total cost"]
                        price_end -= basket[k]["Total cost"]
                       
                        basket_finished = [("Final cost after succesful removal of item ",price_end)]
                        del basket[k]
                        break
                    else:
                        return Response(json.dumps("No item with id:"+str(item)+" exists in your cart."),status=404,mimetype="application/json")
            if len(basket) == 0 :
                return Response(json.dumps("Your cart is empty.",status=500,mimetype="application/json"))
            global whole_cost
            whole_cost = new_price_end
            new_basket_finished = [("Your price after removal: ",new_price_end)]
            return jsonify(basket+new_basket_finished)

#Agora
@app.route('/buyBasket', methods=['GET'])
def buybasket():
    uuid = request.headers.get('Authorization')

    card = request.args.get('card')

    if is_session_valid(uuid)  == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    else:
        if len(card) != 16:
            return Response('Inser card number correctly',status=500,mimetype='application/json')
        if len(card) == 16 :
            return jsonify('Thank you, here is your receipt!','Products',basket,'Total Cost',whole_cost)



#Purchase history
@app.route('/purchaseHistory', methods=['PATCH'])
def purchase_history ():
    uuid = request.headers.get('Authorization')
    if is_session_valid(uuid)  == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')


    else:
        user = users.find_one({"email":user_email})

          
        history = str(basket) 
        user = users.update_one({"email":user_email},
            {"$set":
                {   
                    "orderHistory": (history,'Total Price:',str(whole_cost)), 
                }
            })
        user = users.find_one({"email": user_email})
        return Response(json.dumps('Your Order History: /n'+str(user["orderHistory"])),status=200,mimetype="application/json")
        



#Diagrafi xristi
@app.route('/deleteUser', methods=['DELETE'])
def delete_user():
    uuid= request.headers.get('Authorization')
    if is_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    else:
        msg = ('Your account has been deleted.')
        users.delete_one({"email": user_email})
        return Response(msg, status=200, mimetype='application/json')




#Session kai endpoints gia Admin


admins_sessions = {}

#Admin Session Creation
def create_admin_session(admin_name):
    admin_uuid = str(int(uuid.uuid1())) #39 digit number displayed as string
    admins_sessions[admin_uuid] = (admin_name, time.time())
    return admin_uuid


def admin_session_valid(admin_uuid):
    return admin_uuid in admins_sessions


#Admin Creation
@app.route('/createAdmin', methods=['POST'])
def create_admin():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "email" in data or not "name" in data or not "password" in data or not "category" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    if users.find({"email": data["email"]}).count() == 0:
            admin = {"email": data['email'],"name": data['name'], "password": data['password'], "category":"Admin"}
            users.insert_one(admin)
            # Μήνυμα επιτυχίας
            return Response(data['name'] + " was added to the MongoDB", mimetype='application/json',status=200)  # ΠΡΟΣΘΗΚΗ STATUS

        # Διαφορετικά, αν υπάρχει ήδη κάποιος admin με αυτό το email.
    else:
            # Μήνυμα λάθους (Υπάρχει ήδη κάποιος admin με αυτό το email)
            return Response("An Admin with the given email already exists", mimetype='application/json',status=400)  # ΠΡΟΣΘΗΚΗ STATUS



#Admin login
@app.route('/loginAdmin', methods=['POST'])
def login_admin():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "email" in data or not "password" in data:
        return Response("Information incomplete",status=500,mimetype="application/json")

    # Έλεγχος δεδομένων username / password
    # Αν η αυθεντικοποίηση είναι επιτυχής. 
    if users.find({'$and':[{"email":data["email"]},{"password":data["password"]},{"category":"Admin"} ]}).count() != 0 :
        
    
        admin_uuid=create_admin_session(users.find({"email":data["email"]}))
        res = {"uuid": admin_uuid, "email": data['email']}
        return Response(json.dumps(res), mimetype='application/json',status=200) # ΠΡΟΣΘΗΚΗ STATUS

    # Διαφορετικά, αν η αυθεντικοποίηση είναι ανεπιτυχής.
    else:
        # Μήνυμα λάθους (Λάθος username ή password)
        return Response("Wrong email or password.",mimetype='application/json',status=400,) # ΠΡΟΣΘΗΚΗ STATUS


#Admin create product
@app.route('/createProduct', methods=['PUT'])
def create_product():
    uuid= request.headers.get('Authorization')
    if admin_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    else:
        try:
            data = json.loads(request.data)
        except Exception as e:
            return Response("bad json content",status=500,mimetype='application/json')
        if data == None:
            return Response("bad request",status=500,mimetype='application/json')
        if not "name" in data or not "price" in data or not "description" in data or not "category" in data or not "stock" in data:
            return Response("Information incomplete",status=500,mimetype="application/json")
        if products.find({'$and':[{"name":data["name"]}, {"price":data["price"]}, {"description":data["description"]},{"category":data["category"]}, {"stock":data["stock"]}] }) == 0 :
            product = {"name":data["name"], "price":data["price"], "description":data["description"], "category":data['category'], "stock":data['stock']}
            products.insert_one(product)
            return Response("The product was added to the collection.",status=200,mimetype="application/json")
        else :
            return Response("The product already exists.",status=400,mimetype='application/json')



#Admin Delete Product
@app.route('/deleteProduct/<string:_id>', methods=['DELETE'])
def delete_product(_id):
    uuid= request.headers.get('Authorization')
    if admin_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    else:
        product = products.find_one({"_id":ObjectId(_id)})
        if product != None:
                msg = (product['name']+' was deleted.')
                products.delete_one({"_id": ObjectId(_id)})
                return Response(msg, status=200, mimetype='application/json')
        else:
            msg = ("id doesn't match to any product. "+_id)
            return Response(msg,status=400,mimetype='application/json')


#Update proiontos
@app.route ('/updateProduct/<string:_id>', methods=['PUT'])
def update_product(_id):
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
       return Response("bad request",status=500,mimetype='application/json')

    uuid= request.headers.get('Authorization')
    if admin_session_valid(uuid) == False :
        return Response("User was not authedicated ", status=401, mimetype='application/json')
    else:
        if data["_id"] in data: 
                try:
                    product = products.update_one({"_id":data["_id"]},
                    {"$set": 
                        {
                            "name": str(data["name"]),
                            "price": float(data["price"]),
                            "description": str(data["description"]),
                            "stock": int(data["stock"]),
                            "category":str(data["category"])                                                                                                                           
                        }
                    }) 
                    product = products.find_one({"_id":data["_id"]})
                    return jsonify("Updated Product successfully :",product)
                except Exception as e:
                    return Response("No product with this id exists.",status=500,mimetype="application/json")



if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)