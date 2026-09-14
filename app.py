from flask import Flask, render_template, request, send_file
import fitz  # PyMuPDF
import io
import re

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    platform = request.form.get('platform')
    pdf_file = request.files.get('pdf_file')
    
    # Checkbox settings
    sort_transparent = request.form.get('sort_transparent') == 'on'
    sort_logistics = request.form.get('sort_logistics') == 'on'
    sort_sku = request.form.get('sort_sku') == 'on'
    remove_invoice = request.form.get('remove_invoice') == 'on'
    print_sku = request.form.get('print_sku') == 'on'
    print_page_numbers = request.form.get('print_page_numbers') == 'on'
    
    if not pdf_file or pdf_file.filename == '':
        return "Error: Koi file upload nahi ki gayi!", 400
        
    try:
        file_bytes = pdf_file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        output_doc = fitz.open() 
        
        # ==========================================
        # 1. AMAZON LOGIC 
        # ==========================================
        if platform == 'amazon':
            page_pairs = []
            
            for i in range(0, len(doc), 2):
                label_idx = i
                invoice_idx = i + 1 if (i + 1) < len(doc) else None
                sku = "SKU_NOT_FOUND"
                qty = "1"
                
                if invoice_idx is not None:
                    invoice_text = doc[invoice_idx].get_text("text").replace('\n', ' ')
                    match = re.search(r'(B[0-9A-Z]{9})\s*\(([^)]+)\)', invoice_text)
                    if match:
                        asin = match.group(1)
                        sku = match.group(2).strip()
                        
                        qty_pattern = re.escape(asin) + r'.*?(?:HSN:\S+\s+)?[\d.,]+\s+(?:-[\d.,]+\s+)?(\d+)\s+[\d.,]+\s+[\d.,]+%'
                        qty_match = re.search(qty_pattern, invoice_text)
                        if qty_match:
                            qty = qty_match.group(1)
                
                sku = re.sub(r'[\\/*?:"<>|]', "", sku)
                page_pairs.append({'sku': sku, 'qty': qty, 'label_idx': label_idx, 'invoice_idx': invoice_idx})

            if sort_sku:
                page_pairs = sorted(page_pairs, key=lambda x: x['sku'])

            for pair in page_pairs:
                output_doc.insert_pdf(doc, from_page=pair['label_idx'], to_page=pair['label_idx'])
                new_label_page = output_doc[-1]
                
                if print_sku and pair['sku'] != "SKU_NOT_FOUND":
                    y_pos = 670  
                    x_pos = 70   
                    bg_rect = fitz.Rect(x_pos - 5, y_pos - 15, x_pos + 380, y_pos + 5)
                    new_label_page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1))
                    p = fitz.Point(x_pos, y_pos) 
                    
                    print_text = f"SKU: {pair['sku'][:35]} | QTY: {pair['qty']}"
                    new_label_page.insert_text(p, print_text, fontsize=14, fontname="helv", color=(0, 0, 0))
                
                if not remove_invoice and pair['invoice_idx'] is not None:
                    output_doc.insert_pdf(doc, from_page=pair['invoice_idx'], to_page=pair['invoice_idx'])

        # ==========================================
        # 2. FLIPKART LOGIC 
        # ==========================================
        elif platform == 'flipkart':
            page_data = []
            
            for i in range(len(doc)):
                page = doc[i]
                flat_text = page.get_text("text").replace('\n', ' ')
                
                sku = "Unknown_SKU"
                logistics = "Unknown_Courier"
                is_transparent = "2_Normal"
                
                if re.search(r'Use Transparent Packaging', flat_text, re.IGNORECASE):
                    is_transparent = "1_Transparent"

                logistics_match = re.search(r'(E-Kart Logistics|E Kart Logistics|Delhivery|Shadowfax|Xpressbees|Ecom Express|Bluedart)', flat_text, re.IGNORECASE)
                if logistics_match:
                    logistics = logistics_match.group(1).upper().replace('E KART', 'E-KART')
                
                sku_match = re.search(r'SKU ID\s*\|\s*Description(.*?)\|', flat_text, re.IGNORECASE)
                if sku_match:
                    raw_sku = sku_match.group(1)
                    raw_sku = raw_sku.replace('QTY', '').replace('qty', '').strip()
                    sku = re.sub(r'^\d+\s+', '', raw_sku)
                else:
                    sku_match_alt = re.search(r'([^|\s]+)\s*\|\s*(?:IMEI/SrNo|Not eligible for return)', flat_text)
                    if sku_match_alt:
                        sku = sku_match_alt.group(1).strip()
                
                sku = re.sub(r'[\\/*?:"<>|]', "", sku).strip()
                page_data.append({
                    'page_idx': i, 
                    'sku': sku, 
                    'logistics': logistics,
                    'is_transparent': is_transparent
                })

            if sort_transparent or sort_logistics or sort_sku:
                page_data = sorted(page_data, key=lambda x: (
                    x['is_transparent'] if sort_transparent else "",
                    x['logistics'] if sort_logistics else "",
                    x['sku'] if sort_sku else ""
                ))

            for data in page_data:
                # Sirf page add kar rahe hain, CROP abhi nahi karenge
                output_doc.insert_pdf(doc, from_page=data['page_idx'], to_page=data['page_idx'])

        # ==========================================
        # 3. MEESHO LOGIC
        # ==========================================
        elif platform == 'meesho':
            page_data = []
            
            for i in range(len(doc)):
                page = doc[i]
                text = page.get_text("text")
                sku = "Unknown_SKU"
                
                sku_match_1 = re.search(r'SKU\n(.*?)\nSize', text, re.IGNORECASE)
                sku_match_2 = re.search(r'SKU\nSize\nQty\nColor\nOrder No\.\n(.*?)\n', text, re.IGNORECASE)
                
                if sku_match_1:
                    sku = sku_match_1.group(1).strip()
                elif sku_match_2:
                    sku = sku_match_2.group(1).strip()
                
                sku = re.sub(r'[\\/*?:"<>|]', "", sku).strip()
                page_data.append({'page_idx': i, 'sku': sku})

            if sort_sku:
                page_data = sorted(page_data, key=lambda x: x['sku'])

            for data in page_data:
                output_doc.insert_pdf(doc, from_page=data['page_idx'], to_page=data['page_idx'])

        else:
            for i in range(len(doc)):
                output_doc.insert_pdf(doc, from_page=i, to_page=i)

        # =========================================================
        # 4. PAGE NUMBERS & FINAL CROP (NO BLACK BOX)
        # =========================================================
        for i in range(len(output_doc)):
            page = output_doc[i]
            num_text = str(i + 1)
            
            if platform == 'flipkart':
                # PEHLE NUMBER LIKHENGE
                if print_page_numbers:
                    # Label crop area: 186, 25, 409, 386. Hum is area ke andar draw karenge.
                    x_pos = 409 - 30  # Right margin ke paas
                    y_pos = 25 + 15   # Top margin ke thoda neeche
                    
                    p_pos = fitz.Point(x_pos, y_pos)
                    # Sirf black text insert kar rahe hain (color=(0,0,0))
                    page.insert_text(p_pos, num_text, fontsize=6, fontname="helv", color=(0, 0, 0), overlay=True)
                
                # USKE BAAD CROP KARENGE
                if remove_invoice:
                    crop_rect = fitz.Rect(186, 25, 409, 386)
                    page.set_cropbox(crop_rect)

            elif platform == 'meesho':
                if print_page_numbers:
                    cb = page.cropbox  
                    x_pos = cb.x1 - 40  
                    y_pos = cb.y1 - 20  
                    
                    p_pos = fitz.Point(x_pos, y_pos)
                    page.insert_text(p_pos, num_text, fontsize=14, fontname="helv", color=(0, 0, 0), overlay=True)

            else:
                # Amazon & Others
                if print_page_numbers:
                    cb = page.cropbox  
                    x_pos = cb.x1 - 40  
                    y_pos = cb.y0 + 25  
                    
                    p_pos = fitz.Point(x_pos, y_pos)
                    page.insert_text(p_pos, num_text, fontsize=14, fontname="helv", color=(0, 0, 0), overlay=True)

        output_pdf = io.BytesIO()
        output_doc.save(output_pdf)
        output_pdf.seek(0)
        
        output_doc.close()
        doc.close()
        
        return send_file(
            output_pdf, 
            as_attachment=True, 
            download_name=f"{platform.capitalize()}_Processed_Labels.pdf", 
            mimetype="application/pdf"
        )
        
    except Exception as e:
        return f"System Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)