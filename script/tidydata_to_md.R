#!/usr/bin/env Rscript

# Data Analysis Script for Excel File
# This script explores the structure and contents of Excel files
# Usage: Rscript tidydata_to_md <excel_file_path>

# Load required libraries
suppressPackageStartupMessages({
  library(tidyverse)
  library(readxl)
})

# Function to safely discover Excel file structure
discover_excel_structure <- function(file_path) {
  tryCatch({
    # Get all sheet names
    sheet_names <- excel_sheets(file_path)
    cat("Found", length(sheet_names), "sheet(s):\n", file = stderr())
    for (i in seq_along(sheet_names)) {
      cat(sprintf("  %d. %s\n", i, sheet_names[i]), file = stderr())
    }
    sheet_names
  }, error = function(e) {
    cat("Error accessing Excel file:", e$message, "\n", file = stderr())
    NULL
  })
}

# Function to analyze a single sheet
analyze_sheet <- function(file_path, sheet_name) {
  tryCatch({
    # Read the sheet
    data <- read_excel(file_path, sheet = sheet_name)

    # Basic information
    sheet_info <- list(
      sheet_name = sheet_name,
      dimensions = dim(data),
      column_names = colnames(data),
      column_types = sapply(data, function(x) class(x)[1]),
      missing_counts = sapply(data, function(x) sum(is.na(x))),
      unique_values_sample = list()
    )

    # For each column, get sample of unique values (first 10)
    for (col in colnames(data)) {
      unique_vals <- unique(data[[col]])
      unique_vals <- unique_vals[!is.na(unique_vals)]
      if (length(unique_vals) > 10) {
        sheet_info$unique_values_sample[[col]] <-
          c(head(unique_vals, 10), "...")
      } else {
        sheet_info$unique_values_sample[[col]] <- unique_vals
      }
    }

    list(info = sheet_info)
  }, error = function(e) {
    cat("Error reading sheet", sheet_name, ":", e$message, "\n",
        file = stderr())
    NULL
  })
}

# Function to generate detailed summary for a sheet
generate_sheet_summary <- function(sheet_data, sheet_name) {
  if (is.null(sheet_data)) {
    paste("Could not analyze sheet:", sheet_name)
  } else {
    info <- sheet_data$info

    summary_text <- paste0(
      "## Sheet: ", sheet_name, "\n\n",
      "- Dimensions: ", info$dimensions[1], " rows × ",
      info$dimensions[2], " columns\n",
      "- Total cells: ", prod(info$dimensions), "\n\n",
      "### Column Information:\n"
    )

    for (i in seq_along(info$column_names)) {
      col_name <- info$column_names[i]
      col_type <- info$column_types[i]
      missing_count <- info$missing_counts[i]
      unique_sample <- info$unique_values_sample[[col_name]]

      summary_text <- paste0(summary_text,
        sprintf("**%d. %s** (%s)\n", i, col_name, col_type),
        sprintf("  - Missing values: %d\n", missing_count),
        sprintf("  - Sample values: %s\n\n",
                paste(head(unique_sample, 5), collapse = ", "))
      )
    }

    summary_text
  }
}

# Main analysis function
main_analysis <- function(file_path) {
  cat("=== Excel File Structure Analysis ===\n\n", file = stderr())
  cat("Analyzing file:", file_path, "\n\n", file = stderr())

  # Discover Excel structure
  sheet_names <- discover_excel_structure(file_path)

  if (is.null(sheet_names)) {
    cat("Analysis terminated due to file access error.\n", file = stderr())
    invisible(NULL)
  } else {
    # Analyze each sheet
    all_sheets <- list()
    sheet_summaries <- list()

    for (sheet_name in sheet_names) {
      cat("\nAnalyzing sheet:", sheet_name, "...\n", file = stderr())
      sheet_data <- analyze_sheet(file_path, sheet_name)

      if (!is.null(sheet_data)) {
        all_sheets[[sheet_name]] <- sheet_data
        sheet_summaries[[sheet_name]] <-
          generate_sheet_summary(sheet_data, sheet_name)

        # Print basic info to stderr
        cat("  - Dimensions:", sheet_data$info$dimensions[1], "×",
            sheet_data$info$dimensions[2], "\n", file = stderr())
        cat("  - Columns:", length(sheet_data$info$column_names), "\n",
            file = stderr())
      }
    }

    # Return comprehensive results
    list(
      file_path = file_path,
      sheet_names = sheet_names,
      sheet_data = all_sheets,
      sheet_summaries = sheet_summaries
    )
  }
}

# Function to generate markdown content
generate_markdown_content <- function(results) {
  if (is.null(results)) {
    ""
  } else {
    # Create markdown content
    md_content <- paste0(
      "# Data Structure Analysis\n\n",
      "**File:** ", results$file_path, "\n",
      "**Analysis Date:** ", Sys.Date(), "\n\n",
      "## Overview\n\n",
      "The Excel file contains ", length(results$sheet_names), " sheet(s):\n"
    )

    for (i in seq_along(results$sheet_names)) {
      sheet_name <- results$sheet_names[i]
      if (sheet_name %in% names(results$sheet_data)) {
        dims <- results$sheet_data[[sheet_name]]$info$dimensions
        md_content <- paste0(md_content,
          sprintf("%d. **%s** (%d rows × %d columns)\n",
                  i, sheet_name, dims[1], dims[2])
        )
      } else {
        md_content <- paste0(md_content,
          sprintf("%d. **%s** (could not analyze)\n", i, sheet_name)
        )
      }
    }

    md_content <- paste0(md_content, "\n---\n\n")

    # Add detailed summaries for each sheet
    for (sheet_name in names(results$sheet_summaries)) {
      md_content <- paste0(md_content, results$sheet_summaries[[sheet_name]],
                           "\n---\n\n")
    }

    md_content
  }
}

# Run analysis if script is executed directly
if (!interactive()) {
  # Get command line arguments
  args <- commandArgs(trailingOnly = TRUE)
  
  if (length(args) == 0) {
    cat("Usage: Rscript analyze_datafile.R <excel_file_path>\n",
        file = stderr())
    quit(status = 1)
  }
  
  file_path <- args[1]
  
  # Check if file exists
  if (!file.exists(file_path)) {
    cat("Error: File does not exist:", file_path, "\n", file = stderr())
    quit(status = 1)
  }
  
  # Run analysis
  results <- main_analysis(file_path)
  
  if (!is.null(results)) {
    # Output markdown to stdout
    markdown_content <- generate_markdown_content(results)
    cat(markdown_content)
    
    cat("\nAnalysis complete!\n", file = stderr())
  } else {
    quit(status = 1)
  }
}

# If sourced, make functions available
if (interactive()) {
  cat("Data analysis functions loaded.\n", file = stderr())
  cat("Available functions:\n", file = stderr())
  cat("- main_analysis(file_path)\n", file = stderr())
  cat("- generate_markdown_content(results)\n", file = stderr())
}