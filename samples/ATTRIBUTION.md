# Sample attribution

The `a_`, `b_` and `c_` invoices are synthetic; the `r_` invoices are real and not distributed (see below). The PDFs are unmodified copies; the `*.expected.json` labels were written for this
project from the PDF text (the datasets' own answer keys were used only as a cross-check).

## Files starting with `a_`

Invoice Extraction Benchmark v1, (c) 2026 InvoiceParser Pro, licensed CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/).
Source: https://huggingface.co/datasets/drew-ipp/invoice-extraction-benchmark (corpus/v1/documents/).
The file name after `a_` is the benchmark's document id.

## Files starting with `b_`

InvoiceBenchmark by Jakob Neugebauer, 2026, licensed MIT (stated in the dataset card).
Source: https://huggingface.co/datasets/jngb-labs/InvoiceBenchmark (output/pdf/).
The file name after `b_` is the invoice id.

`dev/a_currency-nad-bare-dollar.pdf` was added later (D25) from the same Invoice Extraction Benchmark v1 source and licence;
its SHA-256 matches the benchmark's answer file (`f0d5c7ac...0841c1`).

The 25 `a_` files added in D30 are further documents from the same Invoice Extraction Benchmark v1 source and licence. Each PDF's SHA-256
matches the benchmark's manifest. Their labels include line items (D34).

## Files starting with `c_`

Sinabis Green Energy – Synthetic Document Dataset (1M PDFs), Sinabis GmbH (2026), licensed CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/).
Source: https://huggingface.co/datasets/sinabis-group/sinabis-1m-synthetic-pdf (`Sinabis_1M_pdfs_part_01.zip`, `pdf/invoice/`).
The file name after `c_` is the file's name in the archive. The PDFs are unmodified; labels include line items (D34).

## Files starting with `r_`

Real invoices received by the project owner. They are not distributed: they live in the git-ignored `samples/private/` folder.
