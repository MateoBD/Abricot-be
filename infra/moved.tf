# Lambdas

moved {
  from = aws_lambda_function.this["health"]
  to   = module.lambda["health"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["users_service"]
  to   = module.lambda["users_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["catalog_service"]
  to   = module.lambda["catalog_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["orders_service"]
  to   = module.lambda["orders_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["restaurants_service"]
  to   = module.lambda["restaurants_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["reservations_service"]
  to   = module.lambda["reservations_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["promotions_service"]
  to   = module.lambda["promotions_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["analytics_service"]
  to   = module.lambda["analytics_service"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["email_worker"]
  to   = module.lambda["email_worker"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["analytics_worker"]
  to   = module.lambda["analytics_worker"].aws_lambda_function.this
}

moved {
  from = aws_lambda_function.this["db_migrate"]
  to   = module.lambda["db_migrate"].aws_lambda_function.this
}

# Lambda artifacts bucket

moved {
  from = aws_s3_bucket.lambda_artifacts
  to   = module.lambda_artifacts_bucket.aws_s3_bucket.this[0]
}

moved {
  from = aws_s3_bucket_versioning.lambda_artifacts
  to   = module.lambda_artifacts_bucket.aws_s3_bucket_versioning.this[0]
}

moved {
  from = aws_s3_bucket_public_access_block.lambda_artifacts
  to   = module.lambda_artifacts_bucket.aws_s3_bucket_public_access_block.this[0]
}

moved {
  from = aws_s3_bucket_server_side_encryption_configuration.lambda_artifacts
  to   = module.lambda_artifacts_bucket.aws_s3_bucket_server_side_encryption_configuration.this[0]
}

# API Gateway routes

moved {
  from = aws_apigatewayv2_route.health
  to   = aws_apigatewayv2_route.this["health"]
}

moved {
  from = aws_apigatewayv2_route.callback
  to   = aws_apigatewayv2_route.this["callback"]
}

moved {
  from = aws_apigatewayv2_route.auth_test
  to   = aws_apigatewayv2_route.this["auth_test"]
}

moved {
  from = aws_apigatewayv2_route.users_post[0]
  to   = aws_apigatewayv2_route.this["users_post"]
}

moved {
  from = aws_apigatewayv2_route.users_get[0]
  to   = aws_apigatewayv2_route.this["users_get"]
}

moved {
  from = aws_apigatewayv2_route.users_put[0]
  to   = aws_apigatewayv2_route.this["users_put"]
}

moved {
  from = aws_apigatewayv2_route.users_restaurants_list[0]
  to   = aws_apigatewayv2_route.this["users_restaurants_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_post"]
}

moved {
  from = aws_apigatewayv2_route.catalog_lookups[0]
  to   = aws_apigatewayv2_route.this["catalog_lookups"]
}

moved {
  from = aws_apigatewayv2_route.catalog_restaurants_list[0]
  to   = aws_apigatewayv2_route.this["catalog_restaurants_list"]
}

moved {
  from = aws_apigatewayv2_route.catalog_restaurant_detail[0]
  to   = aws_apigatewayv2_route.this["catalog_restaurant_detail"]
}

moved {
  from = aws_apigatewayv2_route.catalog_restaurant_menus[0]
  to   = aws_apigatewayv2_route.this["catalog_restaurant_menus"]
}

moved {
  from = aws_apigatewayv2_route.orders_create[0]
  to   = aws_apigatewayv2_route.this["orders_create"]
}

moved {
  from = aws_apigatewayv2_route.orders_user_list[0]
  to   = aws_apigatewayv2_route.this["orders_user_list"]
}

moved {
  from = aws_apigatewayv2_route.orders_restaurant_list[0]
  to   = aws_apigatewayv2_route.this["orders_restaurant_list"]
}

moved {
  from = aws_apigatewayv2_route.orders_restaurant_detail[0]
  to   = aws_apigatewayv2_route.this["orders_restaurant_detail"]
}

moved {
  from = aws_apigatewayv2_route.orders_restaurant_patch[0]
  to   = aws_apigatewayv2_route.this["orders_restaurant_patch"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_review_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_review_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admins_list[0]
  to   = aws_apigatewayv2_route.this["restaurants_admins_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admins_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_admins_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admins_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_admins_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menus_list[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menus_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menus_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menus_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menus_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_menus_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menu_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menu_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menu_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menu_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menu_patch[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menu_patch"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_patch[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_patch"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_admin_menu_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_admin_menu_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_categories_list[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_categories_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_categories_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_categories_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_category_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_category_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_category_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_category_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_category_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_category_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_items_list[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_items_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_items_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_items_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_item_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_item_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_item_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_item_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_menu_item_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_menu_item_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_tables_list[0]
  to   = aws_apigatewayv2_route.this["restaurants_tables_list"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_tables_post[0]
  to   = aws_apigatewayv2_route.this["restaurants_tables_post"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_table_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_table_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_table_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_table_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_table_delete[0]
  to   = aws_apigatewayv2_route.this["restaurants_table_delete"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_business_hours_get[0]
  to   = aws_apigatewayv2_route.this["restaurants_business_hours_get"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_business_hours_put[0]
  to   = aws_apigatewayv2_route.this["restaurants_business_hours_put"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_availability[0]
  to   = aws_apigatewayv2_route.this["restaurants_availability"]
}

moved {
  from = aws_apigatewayv2_route.restaurants_public_availability[0]
  to   = aws_apigatewayv2_route.this["restaurants_public_availability"]
}

moved {
  from = aws_apigatewayv2_route.reservations_create[0]
  to   = aws_apigatewayv2_route.this["reservations_create"]
}

moved {
  from = aws_apigatewayv2_route.reservations_create_public[0]
  to   = aws_apigatewayv2_route.this["reservations_create_public"]
}

moved {
  from = aws_apigatewayv2_route.reservations_restaurant_list[0]
  to   = aws_apigatewayv2_route.this["reservations_restaurant_list"]
}

moved {
  from = aws_apigatewayv2_route.reservations_get[0]
  to   = aws_apigatewayv2_route.this["reservations_get"]
}

moved {
  from = aws_apigatewayv2_route.reservations_patch[0]
  to   = aws_apigatewayv2_route.this["reservations_patch"]
}

moved {
  from = aws_apigatewayv2_route.reservations_user_list[0]
  to   = aws_apigatewayv2_route.this["reservations_user_list"]
}

moved {
  from = aws_apigatewayv2_route.promotions_list[0]
  to   = aws_apigatewayv2_route.this["promotions_list"]
}

moved {
  from = aws_apigatewayv2_route.promotions_create[0]
  to   = aws_apigatewayv2_route.this["promotions_create"]
}

moved {
  from = aws_apigatewayv2_route.promotions_get[0]
  to   = aws_apigatewayv2_route.this["promotions_get"]
}

moved {
  from = aws_apigatewayv2_route.promotions_delete[0]
  to   = aws_apigatewayv2_route.this["promotions_delete"]
}

moved {
  from = aws_apigatewayv2_route.analytics_get[0]
  to   = aws_apigatewayv2_route.this["analytics_get"]
}
