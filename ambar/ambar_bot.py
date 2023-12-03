import os
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, Updater
from ambar_inventario import search_products_by_sku, update_hook_by_sku, save_product_to_db

load_dotenv(".env.telegram")
TOKEN = os.environ.get('ambar_wmsBot')

def search_product(update: Update, context: CallbackContext) -> None:
    context.user_data['action'] = 'search_product'
    update.message.reply_text('Por favor, proporciona los últimos 4 dígitos del SKU.')

def set_product_hook(update: Update, context: CallbackContext) -> None:
    context.user_data['action'] = 'set_hook'
    update.message.reply_text('Por favor, proporciona los últimos 4 dígitos del SKU.')

def add_product(update: Update, context: CallbackContext) -> None:
    context.user_data['action'] = 'add_product'
    update.message.reply_text('Por favor, proporciona el SKU del producto.')


def show_menu(update: Update, context: CallbackContext) -> None:
    keyboard = [
        ["Buscar producto", "Colgar producto"],
        ["Agregar producto", "Mas Opciones"]  # Add more buttons as needed
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text('Opciones:', reply_markup=reply_markup)



def handle_message(update: Update, context: CallbackContext) -> None:
    message = update.message.text
    if message == "Buscar producto":
        search_product(update, context)
        return
    elif message == "Colgar producto":
        set_product_hook(update, context)
        return
    elif message == "Agregar producto":
        add_product(update, context)
        return
    elif message == "Mas Opciones":
        show_menu(update, context)
        return

    if context.user_data.get('set_hook'): 
        new_hook = message
        sku_ending = context.user_data.get('sku_ending')
        update_hook_by_sku(sku_ending, new_hook)
        update.message.reply_text(f"El gancho para el SKU que termina en {sku_ending} ha sido actualizado a {new_hook}.")
        context.user_data.clear() 
        show_menu(update, context)
        return 

    user_action = context.user_data.get('action')
    sku_ending = message[-4:] if user_action in ['search_product', 'set_hook'] else None
    
    if user_action == 'search_product':
        sku_ending = message[-4:]
        products = search_products_by_sku(sku_ending)
        
        # If no products are found
        if not products:
            update.message.reply_text(f"No se encontraron productos con SKU que termina en {sku_ending}.")
            context.user_data['action'] = None
            context.user_data.clear()
            show_menu(update, context)
        
        sku_set = {product[0] for product in products}
        response_messages = []

        for sku in sku_set:
            # Gather all products with this SKU
            specific_products = [prod for prod in products if prod[0] == sku]
            hook = specific_products[0][1]
            
            # Gather the unique models (color/size combinations) for this SKU
            models = {f"{prod[2]}/{prod[3]}" for prod in specific_products if prod[2] and prod[3]}
            formatted_models = ', '.join(models) if models else "Sin modelo específico"
            
            response_messages.append(f"SKU: {sku} está ubicado en el gancho {hook}. Los modelos disponibles son: {formatted_models}.")

        # Send the responses
        for msg in response_messages:
            update.message.reply_text(msg)
        context.user_data.clear()
        show_menu(update, context)

    elif context.user_data.get('change_hook'):
        if message.lower() in ["sí", "si"]:
            update.message.reply_text("Por favor, proporciona el nuevo gancho.")
            context.user_data['set_hook'] = True
            context.user_data.pop('change_hook', None)  # Reset change_hook after reading its value
        else:
            update.message.reply_text("Entendido. No se ha realizado ningún cambio.")
            context.user_data.clear()
            show_menu(update, context)
            return

    elif user_action == 'set_hook':
        sku_ending = message[-4:]
        products = search_products_by_sku(sku_ending)
        
        # If no products are found
        if not products:
            update.message.reply_text(f"No se encontraron productos con SKU que termina en {sku_ending}.")
            context.user_data.clear()
            show_menu(update, context)
            return  # End here if no products are found

        current_hook = products[0][1]
        if current_hook:
            update.message.reply_text(f"El SKU que termina en {sku_ending} ya está colgado en el gancho {current_hook}. ¿Quieres cambiarlo? (Sí/No)")
            context.user_data['change_hook'] = True
            context.user_data['sku_ending'] = sku_ending
        else:
            update.message.reply_text(f"Por favor, proporciona el gancho para el SKU que termina en {sku_ending}.")
            context.user_data['set_hook'] = True
            context.user_data['sku_ending'] = sku_ending

    elif context.user_data.get('set_hook'):
        new_hook = message
        sku_ending = context.user_data.get('sku_ending')
        update_hook_by_sku(sku_ending, new_hook)
        update.message.reply_text(f"El gancho para el SKU que termina en {sku_ending} ha sido actualizado a {new_hook}.")
        context.user_data.clear() 
        show_menu(update, context)

    elif user_action == 'add_product':
        # First step: Getting the SKU of the new product
        if not context.user_data.get('new_product'):
            context.user_data['new_product'] = {'sku': message}
            update.message.reply_text('¿El producto tiene variantes como color y tamaño? (Sí/No)')
            return

        # Check if the product has variants
        if 'has_variants' not in context.user_data['new_product']:
            if message.lower() in ['sí', 'si']:
                context.user_data['new_product']['has_variants'] = True
                update.message.reply_text('¿Cuántas variantes tiene el producto?')
            else:
                context.user_data['new_product']['has_variants'] = False
                update.message.reply_text('Por favor, proporciona el color y tamaño separados por una barra (/). Ejemplo: Rojo/L')
            return

        # Process color/size for products without variants
        if not context.user_data['new_product']['has_variants'] and 'color_size' not in context.user_data['new_product']:
            color, size = message.split('/')
            context.user_data['new_product']['color_size'] = {'color': color, 'size': size}
            update.message.reply_text('¿Cuál es la cantidad para este producto?')  # Ask for quantity
            return

        # Now handle the quantity for products without variants
        if not context.user_data['new_product']['has_variants'] and 'color_size' in context.user_data['new_product'] and 'quantity' not in context.user_data['new_product']:
            context.user_data['new_product']['quantity'] = int(message)
            update.message.reply_text('¿Cuál es el costo por artículo para este producto?')
            return


        # Process color/size for each variant
        if context.user_data['new_product']['has_variants'] and context.user_data['new_product']['variants_added'] < context.user_data['new_product']['variant_count']:
            color, size = message.split('/')
            current_variant = {'color': color, 'size': size}
            context.user_data['new_product'].setdefault('variants', []).append(current_variant)
            
            # Ask for the quantity of the current variant
            update.message.reply_text(f'¿Cuál es la cantidad para el variante {color}/{size}?')
            return

        # Handle quantity input for each variant
        if context.user_data['new_product']['has_variants'] and 'quantity' not in context.user_data['new_product']['variants'][-1]:
            context.user_data['new_product']['variants'][-1]['quantity'] = int(message)
            context.user_data['new_product']['variants_added'] += 1

            # If not all variants added
            if context.user_data['new_product']['variants_added'] < context.user_data['new_product']['variant_count']:
                update.message.reply_text('Por favor, proporciona el color y tamaño del siguiente variante separados por una barra (/). Ejemplo: Rojo/L')
            else:
                update.message.reply_text('Por favor, proporciona el costo por artículo.')
            return


        # Process cost_per_item
        if 'cost_per_item' not in context.user_data['new_product']:
            context.user_data['new_product']['cost_per_item'] = message
            save_product_to_db(context.user_data['new_product'])
            if context.user_data['new_product']['has_variants']:
                variants_details = ', '.join([f"{v['color']}/{v['size']}" for v in context.user_data['new_product']['variants']])
                update.message.reply_text(f"Producto {context.user_data['new_product']['sku']} con variantes {variants_details} y costo {context.user_data['new_product']['cost_per_item']} ha sido agregado.")
            else:
                update.message.reply_text(f"Producto {context.user_data['new_product']['sku']} de color/tamaño {context.user_data['new_product']['color_size']['color']}/{context.user_data['new_product']['color_size']['size']} y costo {context.user_data['new_product']['cost_per_item']} ha sido agregado.")
            context.user_data.clear()
            show_menu(update, context)

    else:
        context.user_data.clear()
        show_menu(update, context)

def main() -> None:
    updater = Updater(token=TOKEN)

    # Add command handlers
    updater.dispatcher.add_handler(CommandHandler('agregarproducto', add_product))
    updater.dispatcher.add_handler(CommandHandler('buscarproducto', search_product))
    updater.dispatcher.add_handler(CommandHandler('colgarproducto', set_product_hook))
    updater.dispatcher.add_handler(CommandHandler('start', show_menu))  # Handling /start command

    # Add message handler
    updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()