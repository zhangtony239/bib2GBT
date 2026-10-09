import json
import re
import sys


def cleanText(text: str) -> str:
    """去除 LaTeX 保护性花括号并压缩空白（GB/T 著录中不保留排版标记）"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = text.replace('{', '').replace('}', '')
    return re.sub(r"\s+", " ", text).strip()


def cleanPages(pages: str) -> str:
    """页码归一化：'3982--3992' -> '3982-3992'"""
    return re.sub(r"-{2,}", "-", pages.replace(' ', '')).strip()


def formatName(name: str) -> str:
    """西文著者 '姓, 名' -> '姓全大写 + 名首字母'，如 'Reimers, Nils' -> 'REIMERS N'"""
    name = cleanText(name).rstrip('.').strip()
    if re.search(r'[\u4e00-\u9fff]', name):  # 中文姓名原样保留
        return name

    if ',' in name:
        family, given = name.split(',', 1)
    else:
        parts = name.split()
        if len(parts) == 1:
            return parts[0].upper()
        if len(parts[0]) > 1 and parts[0] == parts[0].upper():
            # '姓 名' 顺序（如拼音大写姓），姓在前
            family, given = parts[0], ' '.join(parts[1:])
        else:
            # '名 姓' 顺序，取最后一个词为姓
            family, given = parts[-1], ' '.join(parts[:-1])

    initials = [w[0] for w in re.split(r'[\s.]+', given.strip()) if w]
    return (family.strip().upper() + ' ' + ' '.join(initials)).strip()


def formatPeople(raw: str) -> str:
    """著者/编者列表 -> GB/T 格式；超过 3 人只列前 3 人，其后加 ', et al' / ', 等'"""
    raw = cleanText(raw).replace('，', ',').replace('、', ',')

    if raw.find('&') != -1:  # cnki：'姓 名 & 姓 名'，保持原样（仅大写、去点）
        names = [n for n in re.split(r'\s*&\s*|\s+and\s+', raw, flags=re.IGNORECASE) if n.strip()]
        people = [n.replace('.', '').strip().upper() for n in names]
    else:
        names = [n for n in re.split(r'\s+and\s+', raw, flags=re.IGNORECASE) if n.strip()]
        people = [formatName(n) for n in names]

    if not people:
        return ""

    if len(people) > 3:
        first_is_cjk = any('\u4e00' <= ch <= '\u9fff' for ch in people[0])
        etc = ", 等" if first_is_cjk else ", et al"
        return ", ".join(people[:3]) + etc

    return ", ".join(people)


def getAuthor(bibJson):
    return formatPeople(bibJson["author"])


def doiSuffix(bibJson) -> str:
    doi = bibJson.get("doi", bibJson.get("DOI", ""))
    return (" DOI: " + doi + ".") if doi else ""


def type_D(bibJson, reftype, bibtype):
    place = bibJson.get("address", bibJson.get("location", ""))
    school = bibJson.get("school", bibJson.get("institution", ""))
    year = bibJson.get("year", "")

    imprint = (place + ": " if place else "") + school
    if year:
        imprint += (", " if imprint else "") + year

    fileBGT = (getAuthor(bibJson) + ". " +
               bibJson["title"] +
               reftype[bibtype] + ". " +
               imprint + "." + doiSuffix(bibJson)
               )
    return fileBGT


def type_J(bibJson, reftype, bibtype):

    year = bibJson.get("year", "")
    volume = bibJson.get("volume", "")
    number = bibJson.get("number", "")
    pages = cleanPages(bibJson["pages"]) if "pages" in bibJson else ""

    # cnki：只有 number 没有 pages 时，number 实为页码
    if number and not pages:
        pages = cleanPages(number)
        number = ""

    imprint = ""
    if year:
        imprint += ", " + year
    if volume:
        imprint += ", " + volume + (("(" + number + ")") if number else "")
    elif number:
        imprint += "(" + number + ")"
    if pages:
        imprint += ": " + pages

    fileBGT = (getAuthor(bibJson) + ". " +
               bibJson["title"] +
               reftype[bibtype] + ". " +
               bibJson.get("journal", "") +
               imprint + "." + doiSuffix(bibJson)
               )

    return fileBGT


def type_C(bibJson, reftype, bibtype):
    """GB/T 7714 会议录：作者. 题名[C]//编者. 会议录名. 出版地: 出版者, 年: 页码. DOI: ..."""
    editor = formatPeople(bibJson["editor"]) + ". " if "editor" in bibJson else ""
    place = bibJson.get("address", bibJson.get("location", ""))
    publisher = bibJson.get("publisher", "")
    year = bibJson.get("year", "")
    pages = cleanPages(bibJson["pages"]) if "pages" in bibJson else ""

    imprint = ""
    if place or publisher:
        imprint += (place + ": " if place else "") + publisher
    if year:
        imprint += (", " if imprint else "") + year
    if pages:
        imprint += (": " if imprint else "") + pages

    fileBGT = (getAuthor(bibJson) + ". " +
               bibJson["title"] +
               reftype[bibtype] + "//" +
               editor +
               bibJson.get("booktitle", "") +
               (". " + imprint if imprint else "") + "." + doiSuffix(bibJson)
               )

    return fileBGT


def type_N(bibJson, reftype, bibtype):

    place = bibJson.get("address", bibJson.get("location", ""))
    institution = bibJson.get("institution", "")
    year = bibJson.get("year", "")

    imprint = (place + ": " if place else "") + institution
    if year:
        imprint += (", " if imprint else "") + year

    fileBGT = (getAuthor(bibJson) + ". " +
               bibJson["title"] +
               reftype[bibtype] + ". " +
               imprint + "." + doiSuffix(bibJson)
               )

    return fileBGT


def getBibJson(lines: list) -> dict:

    jsonLines =[]
    jsonLines.append('{\r\n')


    for l in lines[1: -1]:
        if (l.find('"') != -1) & (l.find('"') != l.rfind('"')):
            index_1 = l.find("=")
            index_2 = l.find('"')
            index_3 = l.rfind('"')
            l = '"' + l[0: index_1].replace(' ', '') + '":' + l[index_2: index_3] + '",\r\n'   

        else:
            #cnki
            if ((l.find('=') != -1) &
                (l.find('"') == -1) &
                (l.find('{') == -1) &
                (l.find('}') == -1)):

                index_1 = l.find("=")
                index_2 = l.find(',')
                l = '"' + l[0: index_1].replace(' ', '') + '":"' + l[index_1 + 1: index_2].strip() + '",\r\n'
            
            else:
                l = l.replace('{', '"', 1)[::-1].replace('}', '"', 1)[::-1]  # replace the outermost layer only
                index = l.find("=")
                if(index != -1): l = '"' + l[0: index].replace(' ', '') + '":' + l[index + 1: -1] + "\r\n"

        jsonLines.append(l)

    jsonLines.append('}')

    index = jsonLines[-2].rfind('"')
    jsonLines[-2] = jsonLines[-2][0: index] + jsonLines[-2][index: -1].replace(',', '') + "\r\n"
    
    bibJson = json.loads("".join(jsonLines).replace('\r', '').replace('\n', '').replace('\t', '').replace('\\', ''))

    for key in bibJson:
        if isinstance(bibJson[key], str):
            bibJson[key] = cleanText(bibJson[key])

    return bibJson


def mainProscess(bibFile: str) -> list:
    with open(bibFile, "r", encoding='utf-8') as f:
        lines = f.readlines() 

    lines_multibib = []
    lines_singlebib = []

    for l in lines:
        if l == "\n": continue
        # 遇到新的 @ 条目且当前缓存非空时，切出上一条文献
        if l.find('@') != -1 and lines_singlebib:
            lines_multibib.append(lines_singlebib[:])
            lines_singlebib.clear()
        lines_singlebib.append(l)

    if lines_singlebib:
        lines_multibib.append(lines_singlebib[:])


    reftype = {"article": "[J]",
            "mastersthesis": "[D]",
            "phdthesis": "[D]",
            "inproceedings": "[C]",
            "conference": "[C]",
            "book": "[M]",
            "booklet": "[M]",
            "techreport": "[N]",
            "misc": "[P]",
            "manual": "[P]"}


    fileBGT = []

    for _lines in lines_multibib:
   
        index_1 = _lines[0].find('@')
        index_2 = _lines[0].find('{')
    
        if index_2 == -1: index_2 = _lines[0].find('(')
    
        bibtype = _lines[0][index_1 + 1: index_2].replace(' ', '').lower()
    
        # print(bibtype)
    
        index_3 = _lines[-1].rfind(')')
    
        if index_3 != -1:
            _lines[-1] = _lines[-1][0: index_3]
            _lines.append('}')
        
        bibJson = getBibJson(_lines)
    
        match reftype[bibtype]:
            case "[J]":
                fileBGT.append(type_J(bibJson, reftype, bibtype))
            case "[D]":
                fileBGT.append(type_D(bibJson, reftype, bibtype))
            case "[C]":
                fileBGT.append(type_C(bibJson, reftype, bibtype))
            case "[N]":
                fileBGT.append(type_N(bibJson, reftype, bibtype))
            case _:
                fileBGT.append("** 类型不支持 **")

   
    return fileBGT


def main(argv: list | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="bib2gbt",
        description="Convert a BibTeX (.bib) file to GB/T 7714 style references."
    )
    parser.add_argument("bibfile", help="path to the .bib file to convert")
    args = parser.parse_args(argv)

    fileBGT = mainProscess(args.bibfile)
    _count = 1
    for l in fileBGT:
        if fileBGT.__len__() == 1: print(l)
        else:
            print(f'[{_count}]', l)
            _count += 1


if __name__ == "__main__":
    main()
