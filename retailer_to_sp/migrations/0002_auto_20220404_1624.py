# Generated by Django 2.1 on 2022-04-04 16:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
        ('wms', '0001_initial'),
        ('retailer_to_sp', '0001_initial'),
        ('shops', '0001_initial'),
        ('addresses', '0002_auto_20220404_1624'),
        ('products', '0002_auto_20220404_1624'),
        ('pos', '0002_auto_20220404_1624'),
    ]

    operations = [
        migrations.AddField(
            model_name='trip',
            name='seller_shop',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_seller_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='trip',
            name='source_shop',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_source_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='trip',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_mile_trip_updated_by', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='shopcrate',
            name='crate',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_crates', to='wms.Crate'),
        ),
        migrations.AddField(
            model_name='shopcrate',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shopcrate_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='shopcrate',
            name='shop',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='shopcrate',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shopcrate_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='shipmentrescheduling',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rescheduled_by', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='shipmentrescheduling',
            name='shipment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rescheduling_shipment', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='shipmentrescheduling',
            name='trip',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rescheduling_shipment_trip', to='retailer_to_sp.Trip'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingmapping',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackagingmapping_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingmapping',
            name='ordered_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='shipment_product_packaging', to='retailer_to_sp.OrderedProductMapping'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingmapping',
            name='shipment_packaging',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='packaging_details', to='retailer_to_sp.ShipmentPackaging'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingmapping',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackagingmapping_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingbatch',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackagingbatch_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingbatch',
            name='shipment_product_packaging',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='packaging_product_details', to='retailer_to_sp.ShipmentPackagingMapping'),
        ),
        migrations.AddField(
            model_name='shipmentpackagingbatch',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackagingbatch_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='shipmentpackaging',
            name='crate',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='crates_shipments', to='wms.Crate'),
        ),
        migrations.AddField(
            model_name='shipmentpackaging',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackaging_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='shipmentpackaging',
            name='shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='shipment_packaging', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='shipmentpackaging',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_shipmentpackaging_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='shipmentpackaging',
            name='warehouse',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='shipmentnotattempt',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='delivery_person', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='shipmentnotattempt',
            name='shipment',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='not_attempt_shipment', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='shipmentnotattempt',
            name='trip',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='not_attempt_shipment_trip', to='retailer_to_sp.Trip'),
        ),
        migrations.AddField(
            model_name='returnproductmapping',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_last_modified_user_return_product', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='returnproductmapping',
            name='return_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_product_return_product_mapping', to='retailer_to_sp.Return'),
        ),
        migrations.AddField(
            model_name='returnproductmapping',
            name='returned_product',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_product_return_product', to='products.Product'),
        ),
        migrations.AddField(
            model_name='returnitems',
            name='ordered_product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_return_ordered_product', to='retailer_to_sp.OrderedProductMapping'),
        ),
        migrations.AddField(
            model_name='returnitems',
            name='return_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_return_list', to='retailer_to_sp.OrderReturn'),
        ),
        migrations.AddField(
            model_name='return',
            name='invoice_no',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='retailer_to_sp.OrderedProduct', verbose_name='Shipment Id'),
        ),
        migrations.AddField(
            model_name='return',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_last_modified_user_order', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='return',
            name='received_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_ordered_product_received_by_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='return',
            name='shipped_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='return_shipped_product_ordered_by_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='responsecomment',
            name='customer_care',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='customer_care_comments', to='retailer_to_sp.CustomerCare'),
        ),
        migrations.AddField(
            model_name='pickeruserassignmentlog',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.User'),
        ),
        migrations.AddField(
            model_name='pickeruserassignmentlog',
            name='final_user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='pickeruserassignmentlog',
            name='initial_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='pickeruserassignmentlog',
            name='picker_dashboard',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='retailer_to_sp.PickerDashboard'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='picker_order', to='retailer_to_sp.Order'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='picker_boy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='picker_user', to='accounts.UserWithName', verbose_name='Picker Boy'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='qc_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='area_pickings', to='wms.QCArea'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='repackaging',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='picker_repacks', to='products.Repackaging'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='shipment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='picker_shipment', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='pickerdashboard',
            name='zone',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='pickup_dashboard_zone', to='wms.Zone'),
        ),
        migrations.AddField(
            model_name='payment',
            name='order_id',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_payment', to='retailer_to_sp.Order'),
        ),
        migrations.AddField(
            model_name='orderreturn',
            name='order',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_return_order', to='retailer_to_sp.Order'),
        ),
        migrations.AddField(
            model_name='orderreturn',
            name='processed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.User'),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='last_modified_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_last_modified_user_order_product', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='ordered_product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_order_product_order_product_mapping', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_product_order_product', to='products.Product'),
        ),
        migrations.AddField(
            model_name='orderedproductmapping',
            name='retailer_product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_retailer_product_order_product', to='pos.RetailerProduct'),
        ),
        migrations.AddField(
            model_name='orderedproductbatch',
            name='bin',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.BinInventory'),
        ),
        migrations.AddField(
            model_name='orderedproductbatch',
            name='ordered_product_mapping',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_ordered_product_mapping', to='retailer_to_sp.OrderedProductMapping'),
        ),
        migrations.AddField(
            model_name='orderedproductbatch',
            name='pickup',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='wms.Pickup'),
        ),
        migrations.AddField(
            model_name='orderedproductbatch',
            name='pickup_inventory',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_pickup_bin_inv', to='wms.PickupBinInventory'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='current_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='shop_shipments', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_last_modified_user_order', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_order_order_product', to='retailer_to_sp.Order'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='qc_area',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='qc_area_shipment', to='wms.QCArea'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='received_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_ordered_product_received_by_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='orderedproduct',
            name='trip',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_invoice_trip', to='retailer_to_sp.Trip'),
        ),
        migrations.AddField(
            model_name='order',
            name='billing_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_billing_address_order', to='addresses.Address'),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_buyer_order', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='order',
            name='buyer_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_buyer_shop_order', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_person',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='accounts.UserWithName', verbose_name='Delivery Boy'),
        ),
        migrations.AddField(
            model_name='order',
            name='dispatch_center',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dispatch_center_orders', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='order',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_order_modified_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='order',
            name='ordered_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_ordered_by_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='order',
            name='ordered_cart',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_order_cart_mapping', to='retailer_to_sp.Cart'),
        ),
        migrations.AddField(
            model_name='order',
            name='received_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_received_by_user', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='order',
            name='seller_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_seller_shop_order', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_shipping_address_order', to='addresses.Address'),
        ),
        migrations.AddField(
            model_name='note',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_last_modified_user_note', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='note',
            name='shipment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='credit_note', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='note',
            name='shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='credit_notes', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentpackages',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_lastmiletripshipmentpackages_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentpackages',
            name='shipment_packaging',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_mile_trip_packaging_details', to='retailer_to_sp.ShipmentPackaging'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentpackages',
            name='trip_shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_mile_trip_shipment_mapped_packages', to='retailer_to_sp.LastMileTripShipmentMapping'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentpackages',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_lastmiletripshipmentpackages_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentmapping',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_lastmiletripshipmentmapping_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentmapping',
            name='shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_mile_trip_shipment', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentmapping',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='last_mile_trip_shipments_details', to='retailer_to_sp.Trip'),
        ),
        migrations.AddField(
            model_name='lastmiletripshipmentmapping',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_lastmiletripshipmentmapping_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='shipment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, related_name='invoice', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='feedback',
            name='shipment',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='shipment_feedback', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='feedback',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_feedback', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentpackages',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripshipmentpackages_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentpackages',
            name='shipment_packaging',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_packaging_details', to='retailer_to_sp.ShipmentPackaging'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentpackages',
            name='trip_shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_shipment_mapped_packages', to='retailer_to_sp.DispatchTripShipmentMapping'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentpackages',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripshipmentpackages_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentmapping',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripshipmentmapping_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentmapping',
            name='shipment',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_shipment', to='retailer_to_sp.OrderedProduct'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentmapping',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='shipments_details', to='retailer_to_sp.DispatchTrip'),
        ),
        migrations.AddField(
            model_name='dispatchtripshipmentmapping',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripshipmentmapping_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='dispatchtripcratemapping',
            name='crate',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='crate_trips', to='wms.Crate'),
        ),
        migrations.AddField(
            model_name='dispatchtripcratemapping',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripcratemapping_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='dispatchtripcratemapping',
            name='trip',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='trip_empty_crates', to='retailer_to_sp.DispatchTrip'),
        ),
        migrations.AddField(
            model_name='dispatchtripcratemapping',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtripcratemapping_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtrip_created_by', to='accounts.User', verbose_name='Created by'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='delivery_boy',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dispatch_trip_delivered_by_user', to='accounts.UserWithName', verbose_name='Delivery Boy'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='destination_shop',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dispatch_trip_destination_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='seller_shop',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dispatch_trip_seller_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='source_shop',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='dispatch_trip_source_shop', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='dispatchtrip',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='retailer_to_sp_dispatchtrip_updated_by', to='accounts.User', verbose_name='Updated by'),
        ),
        migrations.AddField(
            model_name='customercare',
            name='order_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='retailer_to_sp.Order'),
        ),
        migrations.AddField(
            model_name='creditnote',
            name='order_return',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='credit_note_order_return_mapping', to='retailer_to_sp.OrderReturn', unique=True),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='cart',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_cart_list', to='retailer_to_sp.Cart'),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='cart_product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_cart_product_mapping', to='products.Product'),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='cart_product_price',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_cart_product_price_mapping', to='products.ProductPrice'),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='qty_conversion_unit',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_unit_cart_mapping', to='pos.MeasurementUnit'),
        ),
        migrations.AddField(
            model_name='cartproductmapping',
            name='retailer_product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_cart_retailer_product', to='pos.RetailerProduct'),
        ),
        migrations.AddField(
            model_name='cart',
            name='buyer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_buyer_cart', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='cart',
            name='buyer_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_buyer_shop_cart', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='cart',
            name='last_modified_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_last_modified_user_cart', to='accounts.User'),
        ),
        migrations.AddField(
            model_name='cart',
            name='seller_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_seller_shop_cart', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='bulkorder',
            name='billing_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_billing_address_bulk_order', to='addresses.Address'),
        ),
        migrations.AddField(
            model_name='bulkorder',
            name='buyer_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_bulk_buyer_shop_cart', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='bulkorder',
            name='cart',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_bulk_cart_list', to='retailer_to_sp.Cart'),
        ),
        migrations.AddField(
            model_name='bulkorder',
            name='seller_shop',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_bulk_seller_shop_cart', to='shops.Shop'),
        ),
        migrations.AddField(
            model_name='bulkorder',
            name='shipping_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='rt_shipping_address_bulk_order', to='addresses.Address'),
        ),
        migrations.CreateModel(
            name='Commercial',
            fields=[
            ],
            options={
                'verbose_name': 'Commercial',
                'verbose_name_plural': 'Commercial',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.trip',),
        ),
        migrations.CreateModel(
            name='DeliveryData',
            fields=[
            ],
            options={
                'verbose_name': 'Delivery Performance Dashboard',
                'verbose_name_plural': 'Delivery Performance Dashboard',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.trip',),
        ),
        migrations.CreateModel(
            name='Dispatch',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproduct',),
        ),
        migrations.CreateModel(
            name='DispatchProductMapping',
            fields=[
            ],
            options={
                'verbose_name': 'To be Ship product',
                'verbose_name_plural': 'To be Ship products',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproductmapping',),
        ),
        migrations.CreateModel(
            name='PickerPerformanceData',
            fields=[
            ],
            options={
                'verbose_name': 'Picker Performance Dashboard',
                'verbose_name_plural': 'Picker Performance Dashboard',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.pickerdashboard',),
        ),
        migrations.CreateModel(
            name='Shipment',
            fields=[
            ],
            options={
                'verbose_name': 'Plan Shipment',
                'verbose_name_plural': 'Plan Shipment',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproduct',),
        ),
        migrations.CreateModel(
            name='ShipmentProductMapping',
            fields=[
            ],
            options={
                'verbose_name': 'To be Ship product',
                'verbose_name_plural': 'To be Ship products',
                'proxy': True,
                'indexes': [],
            },
            bases=('retailer_to_sp.orderedproductmapping',),
        ),
    ]
