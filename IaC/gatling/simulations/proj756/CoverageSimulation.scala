package proj756

import scala.concurrent.duration._
import scala.util.Random

import io.gatling.core.Predef._
import io.gatling.http.Predef._

object Utility {
  /*
    Utility to get an Int from an environment variable.
    Return defInt if the environment var does not exist
    or cannot be converted to a string.
  */
  def envVarToInt(ev: String, defInt: Int): Int = {
    try {
      sys.env(ev).toInt
    } catch {
      case e: Exception => defInt
    }
  }

  /*
    Utility to get an environment variable.
    Return defStr if the environment var does not exist.
  */
  def envVar(ev: String, defStr: String): String = {
    sys.env.getOrElse(ev, defStr)
  }
}


object User {

  // val feeder = Iterator.continually(
  //   Map("user_id" -> "02ae7e84-71a5-4e62-ad67-1e9f83cfdbc0")
  // )
  // val feeder = csv("users.csv").eager.random

  var login = exec(
    http("User Login")
    .put("/api/v1/user/login")
    .body(StringBody("""
    {
      "uid": "${user_id}"
    }
    """)).asJson
    .check(status is 200)
    .check(bodyString.saveAs("jwt"))
  )
  .pause(1)

  var logoff = exec(
    http("User Logoff")
    .put("/api/v1/user/logoff")
    .body(StringBody("""
    {
      "jwt": "${jwt}"
    }
    """)).asJson
    .check(status is 200)
  )
  .pause(1)

  val create = exec(
      http("Create User")
      .post("/api/v1/user/")
      .body(StringBody("""
      { 
        "address": "China", 
        "email": "gatling@test.mail", 
        "username": "gatling_test" 
      }
      """)).asJson
      .check(status is 200)
      .check(jsonPath("$.user_id").saveAs("user_id"))
    )
    .pause(1)

  val read = exec(
      http("Read User")
      .get("/api/v1/user/${user_id}")
    )
    .pause(1)

  var update = exec(
      http("Update User")
      .put("/api/v1/user/${user_id}")
      .body(StringBody("""
      { 
        "address": "Canada", 
        "email": "gatling@test-updated.mail", 
        "username": "gatling_test_updated" 
      }
      """)).asJson
    )
    .pause(1)
}

object ShoppingCart {
  var insertItem = exec(
      http("Insert one item to user’s cart")
      .post("/api/v1/user/${user_id}/cart/item")
      .body(StringBody("""
      {
        "item_id": "${item_id}",
        "quantity": 2
      }
      """)).asJson
    )
    .pause(1)

  var listItems = exec(
      http("List items in user’s cart")
      .get("/api/v1/user/${user_id}/cart")
  )

  var deleteItem = exec(
      http("Delete one item from user’s cart")
      .delete("/api/v1/user/${user_id}/cart/item/${item_id}")
  )

  var checkoutItems = exec(
      http("checkout user’s cart")
      .post("/api/v1/user/${user_id}/cart/checkout")
  )
}

object Order {
  val feeder = Iterator.continually(
    Map("order_id" -> Random.nextInt(Integer.MAX_VALUE),
        "user_id" -> "311339d8-c5ac-4a1b-b4c0-4f8ad42b4c79")
  )

  val create = feed(feeder).exec(
      http("Create Order")
      .post("/api/v1/order/${user_id}/${order_id}")
      .body(StringBody("""
      { 
        "price": 2
      }
      """)).asJson	  
      .check(status is 200)
      // .check(jsonPath("$.order_id").saveAs("order_id"))
    )
    .pause(1)

  val read = exec(
      http("List orders")
      .get("/api/v1/order/${user_id}")
    )
    .pause(1)
	
  val readBtId = exec(
      http("Get Order By Order Id")
      .get("/api/v1/order/${user_id}/${order_id}")
    )
    .pause(1)

  var update = exec(
      http("Update Order")
      .put("/api/v1/order/${user_id}/${order_id}")
      .body(StringBody("""
      { 
        "price": 3
      }
      """)).asJson	
    )
    .pause(1)
  var delete = exec(
      http("Delete Order")
	  .delete("/api/v1/order/${user_id}/${order_id}")
  )
}

object Item {
  val feeder = csv("items.csv").eager.random

  val create = feed(feeder).exec(
      http("Create Item")
      .post("/api/v1/item/")
      .body(StringBody("""
      { 
        "item_name": "iPhone12", 
        "item_price": 5999, 
        "item_description": "iPhone12, good quality",
        "item_status": 0
      }
      """)).asJson
      .check(status is 200)
      .check(jsonPath("$.item_id").saveAs("item_id"))
    )
    .pause(1)

  val read = feed(feeder).exec(
      http("Read Item")
      .get("/api/v1/item/${item_id}")
    )
    .pause(1)

  var update = exec(
      http("Update Item")
      .put("/api/v1/item/${item_id}")
      .body(StringBody("""
      { 
        "item_name": "iPhone22", 
        "item_price": 15999, 
        "item_escription": "iPhone22, good quality",
        "item_status": 1
      }
      """)).asJson
    )
    .pause(1)
    var delete = exec(
      http("Delete Item")
	  .delete("/api/v1/item/${item_id}")
  )
}


// Get Cluster IP from CLUSTER_IP environment variable or default to 127.0.0.1 (Minikube)
class ReadTablesSim extends Simulation {
  val httpProtocol = http
    .baseUrl("http://" + Utility.envVar("CLUSTER_IP", "127.0.0.1") + "/")
    .acceptHeader("application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
    .authorizationHeader("Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiZGJmYmMxYzAtMDc4My00ZWQ3LTlkNzgtMDhhYTRhMGNkYTAyIiwidGltZSI6MTYwNzM2NTU0NC42NzIwNTIxfQ.zL4i58j62q8mGUo5a0SQ7MHfukBUel8yl8jGT5XmBPo")
    .acceptLanguageHeader("en-US,en;q=0.5")
}

class CreateAndReadUserSim extends ReadTablesSim {
  val scnCRUDUser = scenario("CRUDUser")
    .exec(User.create)
    .exec(User.login)
    .exec(User.read)
    .exec(User.update)
    .exec(User.logoff)

  val scnCRUDShoppingCart = scenario("CRUDShoppingCart")
    .exec(User.create)
    .exec(Item.create)
    .exec(ShoppingCart.insertItem)
    .exec(Item.create)
    .exec(ShoppingCart.insertItem)
    .exec(ShoppingCart.listItems)
    .exec(ShoppingCart.deleteItem)
    .exec(ShoppingCart.checkoutItems)

  setUp(
    scnCRUDUser.inject(atOnceUsers(Utility.envVarToInt("USERS", 1))),
    scnCRUDShoppingCart.inject(atOnceUsers(Utility.envVarToInt("USERS", 1)))
  ).protocols(httpProtocol)
}

class CreateAndReadOrderSim extends ReadTablesSim {
  val scnCRUDOrder = scenario("CRUDOrder")
    .exec(Order.create)
    .exec(Order.read)
    .exec(Order.update)
    .exec(Order.delete)


  setUp(
    scnCRUDOrder.inject(atOnceUsers(Utility.envVarToInt("USERS", 1)))
  ).protocols(httpProtocol)
}

class CreateAndReadItemSim extends ReadTablesSim {
  val scnCRUDItem = scenario("CRUDItem")
    .exec(Item.create)
    .exec(Item.read)
    .exec(Item.update)
    .exec(Item.delete)


  setUp(
    scnCRUDItem.inject(atOnceUsers(Utility.envVarToInt("USERS", 1)))
  ).protocols(httpProtocol)
}


