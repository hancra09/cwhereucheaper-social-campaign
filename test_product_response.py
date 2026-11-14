import datetime as dt,json,unittest
from product_response import match_request,research,build
NOW=dt.datetime(2026,11,14,11,20,tzinfo=dt.timezone.utc)
PRODUCT={'product_id':23895,'product':'Rhodes Guava Nectar Juice 1lt','retailer':'Superbhyper','price':'9.99','url':'https://superbhyper.co.za/product/rhodes-guava-nectar-juice-1lt/','observed_at':'2026-11-14T10:53:27+00:00'}
PAGE=b'<meta property="og:title" content="Rhodes Guava Nectar Juice 1lt - Superb Hyper"><meta property="product:price:amount" content="9.99"><meta property="product:price:currency" content="ZAR">'
def fetch(url):return json.dumps({'opportunities':[PRODUCT]}).encode() if 'shopping-opportunities' in url else PAGE
class Tests(unittest.TestCase):
 def test_exact_question(self):
  catalog=[(23895,PRODUCT['product'])]
  self.assertEqual(match_request('What is the price of Rhodes Guava Nectar Juice 1lt?',catalog),'23895')
  for bad in ['Is Rhodes Guava Nectar Juice 1lt cheapest?', 'Compare price of Rhodes Guava Nectar Juice 1lt', 'Price Rhodes Guava Nectar Juice?', 'Price Rhodes Guava Nectar Juice 1lt https://evil.test']:
   self.assertIsNone(match_request(bad,catalog))
 def test_exact_live_evidence_and_dated_output(self):
  e=research('23895',fetch,NOW); v=build(e)
  self.assertIn('R9.99',v['script']);self.assertIn('14 November 2026',v['script']);self.assertIn('before delivery',v['script']);self.assertIn('13:20 SAST',v['caption']);self.assertTrue(e['checked_sast'].endswith('+02:00'))
 def test_bad_or_stale_evidence_is_rejected(self):
  with self.assertRaises(ValueError): research('23895',lambda u: fetch(u).replace(b'9.99',b'9.98') if 'shopping-opportunities' not in u else fetch(u),NOW)
  with self.assertRaises(ValueError): research('23895',fetch,NOW+dt.timedelta(hours=7))
  with self.assertRaises(ValueError): research('23895',lambda u: json.dumps({'opportunities':[dict(PRODUCT,url='https://127.0.0.1/')]}).encode(),NOW)
if __name__=='__main__':unittest.main()

class StructuredPageTests(unittest.TestCase):
 def test_only_exact_in_stock_product_offer_is_used(self):
  from product_response import Meta,structured_price
  url='https://animalsfirst.co.za/product/20kg-ideal-adult-dog-food/'
  product={'@type':'Product','@id':url+'#product','name':'20kg Ideal Adult Dog Food','offers':[{'url':url,'priceCurrency':'ZAR','availability':'https://schema.org/InStock','price':'540.00'}]}
  p=Meta();p.feed('<script type="application/ld+json">'+json.dumps({'@graph':[product]})+'</script>')
  self.assertEqual(str(structured_price(p,url,product['name'])),'540.00')
  with self.assertRaises(ValueError):structured_price(p,url,'20kg Different Dog Food')
  product['offers'][0]['availability']='https://schema.org/OutOfStock'
  p=Meta();p.feed('<script type="application/ld+json">'+json.dumps({'@graph':[product]})+'</script>')
  with self.assertRaises(ValueError):structured_price(p,url,product['name'])
