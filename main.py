from core import nlp


def beauty_print_order(order):
    print('----- --- ORDER --- -----')
    print('---- ITEMS ------------')
    print('sl\tqty\titem')
    for i, item in enumerate(order['items'], 1):
        print(f"{i}\t{item['quantity']}\t{item['item']}")
    if 'store' in order:
        print()
        print('STORE:', order['store'])
    print('----- xxx END xxx -----')


if __name__ == '__main__':
    cnlp = nlp.CoffeeNlpCore()
    print('Enter "exit" to quit')
    while True:
        text = input('sent: ')
        if text == 'exit':
            break
        beauty_print_order(cnlp.parse(text))
