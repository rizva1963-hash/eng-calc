# CLAUDE.md

## Reading documents
- Before reading a PDF, Word, Excel or PowerPoint file, convert it to Markdown and read the `.md` instead: `markitdown file.pdf -o file.md`. It uses far fewer tokens than reading the original.
- For large results, read only the parts you need (grep / offset) instead of the whole file.
- Tables in PDFs can lose their layout after conversion; open the original page only if a table is unreadable.
