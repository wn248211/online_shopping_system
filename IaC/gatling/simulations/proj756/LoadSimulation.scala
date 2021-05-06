package proj756

import scala.concurrent.duration._
import scala.math.round

import io.gatling.core.Predef._
import io.gatling.http.Predef._


class UserLoadSim extends ReadTablesSim {
  val scnCRUDUser = scenario("CRUDUser")
    .exec(User.create)
    .repeat(3, "index") {
      exec(User.read, User.update)
    }

  val users = Utility.envVarToInt("USERS", 50)
  
  setUp(
    scnCRUDUser.inject(
      constantUsersPerSec(users) during (10)
    )
  ).protocols(httpProtocol)
}


class ShoppingCartLoadSim extends ReadTablesSim {
  val scnCRUDShoppingCart = scenario("CRUDShoppingCart")
    .exec(User.create)
    .repeat(3, "index") {
      exec(ShoppingCart.insertItem, ShoppingCart.listItems, ShoppingCart.deleteItem)
    }

  val users = Utility.envVarToInt("USERS", 50)

  setUp(
    scnCRUDShoppingCart.inject(
      constantUsersPerSec(users) during (10)
    )
  ).protocols(httpProtocol)
}

class OrderLoadSim extends ReadTablesSim {
  val scnCRUDOrder = scenario("CRUDOrder")
    .exec(Order.create)
    .repeat(3, "index") {
      exec(Order.read, Order.update)
    }
    .exec(Order.delete)

  val users = Utility.envVarToInt("USERS", 50)

  setUp(
    scnCRUDOrder.inject(
      constantUsersPerSec(users) during (10)
    ),
  ).protocols(httpProtocol)
}

class ItemLoadSim extends ReadTablesSim {
  val scnCRUDOrder = scenario("CRUDItem")
    .exec(Item.create)
    .repeat(3, "index") {
      exec(Item.read, Item.update)
    }
    .exec(Item.delete)

  val users = Utility.envVarToInt("USERS", 50)

  setUp(
    scnCRUDOrder.inject(
      constantUsersPerSec(users) during (10)
    ),
  ).protocols(httpProtocol)
}

class LoadSim extends ReadTablesSim {
  val scnAdmin = scenario("Admin")
    .exec(User.create)
    .exec(User.login)
    .exec(User.logoff)
  
  val scnBrowing = scenario("Browsing")
    .exec(User.create)
    .exec(User.login)
    .repeat(5, "index") {
      exec(Item.read)
    }
    .exec(ShoppingCart.listItems)
    .exec(Order.read)
    .exec(User.logoff)
  
  val scnUpdatingSeller = scenario("UpdatingSeller")
    .exec(User.create)
    .exec(User.login)
    .repeat(2, "index") {
      exec(Item.create)
    }
    .exec(User.logoff)
  
  val scnUpdatingBuyer = scenario("UpdatingBuyer")
    .exec(User.create)
    .exec(User.login)
    .repeat(5, "index") {
      exec(Item.read, ShoppingCart.insertItem)
    }
    .exec(ShoppingCart.checkoutItems)
    .exec(User.logoff)
  
  val scnRemoval = scenario("Removal")
    .exec(User.create)
    .exec(User.login)
    .repeat(5, "index") {
      exec(Item.read)
    }
    .exec(ShoppingCart.deleteItem)
    .exec(User.logoff)

  val users = Utility.envVarToInt("USERS", 50)

  setUp(
    scnAdmin.inject(
      constantConcurrentUsers(round(users*0.05).toInt).during(10.minutes)
    ),
    scnBrowing.inject(
      constantConcurrentUsers(round(users*0.45).toInt).during(10.minutes)
    ),
    scnUpdatingSeller.inject(
      constantConcurrentUsers(round(users*0.1).toInt).during(10.minutes)
    ),
    scnUpdatingBuyer.inject(
      constantConcurrentUsers(round(users*0.3).toInt).during(10.minutes)
    ),
    scnRemoval.inject(
      constantConcurrentUsers(round(users*0.1).toInt).during(10.minutes)
    ),
  ).protocols(httpProtocol)
}
