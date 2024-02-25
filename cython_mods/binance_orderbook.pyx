cimport cython
from libc.stdint cimport int64_t  # Import int64_t type


cdef bint qty_at_price_changed(dict local_order_book_side, str price, str qty):
    cdef str old_qty = local_order_book_side.get(price, None)
    if old_qty is None:
        return True

    return float(old_qty) != float(qty)

cdef void refresh_orderbook(dict local_order_book_side, str price, str qty):
    cdef float fqty = float(qty)
    if fqty == 0:
        local_order_book_side.pop(price, None)
    else:
        local_order_book_side[price] = qty

@cython.boundscheck(False)
@cython.wraparound(False)
cpdef dict parser(dict data, dict local_order_book, float avg_volume):
    cdef:
        int64_t finalUpdateId = data['u']  # Use int64_t type here
        int64_t lastUpdateId = local_order_book['lastUpdateId']  # Use int64_t type here
        int64_t timestamp = data['E']  # Use int64_t type here, if needed
        list latest_updates = []
        list bids = data['b']
        list asks = data['a']
        str price, qty, side
        float fqty

    if finalUpdateId <= lastUpdateId:
        return  # Ignore this data

    if local_order_book['lastUpdateId'] is not None and finalUpdateId >= lastUpdateId + 1:
        for bid in bids:
            price, qty = bid
            side = 'bids'
            fqty = float(qty)
            
            if qty_at_price_changed(local_order_book[side], price, qty):
                if fqty > avg_volume:
                    latest_updates.append(
                        {'price': price, 'old_qty': local_order_book[side].get(price, 0), 'new_qty': qty, 'side': side})
                
                refresh_orderbook(local_order_book[side], price, qty)

        for ask in asks:
            price, qty = ask
            side = 'asks'
            fqty = float(qty)
            
            if qty_at_price_changed(local_order_book[side], price, qty):
                if fqty > avg_volume:
                    latest_updates.append(
                        {'price': price, 'old_qty': local_order_book[side].get(price, 0), 'new_qty': qty, 'side': side})
                
                refresh_orderbook(local_order_book[side], price, qty)

        local_order_book['lastUpdateId'] = finalUpdateId

    return {'timestamp': timestamp, 'updates': latest_updates}
