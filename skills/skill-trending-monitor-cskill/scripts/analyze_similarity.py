#!/usr/bin/env python3
"""
Analyze functional similarity between Claude Skills.
Uses TF-IDF vectorization and cosine similarity for text matching.
"""

import os
import re
import math
from collections import Counter
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime
import logging
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.validators.data_validator import DataValidator

logger = logging.getLogger(__name__)

ENGLISH_STOP_WORDS = {
    'a',
    'about',
    'above',
    'across',
    'after',
    'afterwards',
    'again',
    'against',
    'all',
    'almost',
    'alone',
    'along',
    'already',
    'also',
    'although',
    'always',
    'am',
    'among',
    'amongst',
    'amoungst',
    'amount',
    'an',
    'and',
    'another',
    'any',
    'anyhow',
    'anyone',
    'anything',
    'anyway',
    'anywhere',
    'are',
    'around',
    'as',
    'at',
    'back',
    'be',
    'became',
    'because',
    'become',
    'becomes',
    'becoming',
    'been',
    'before',
    'beforehand',
    'behind',
    'being',
    'below',
    'beside',
    'besides',
    'between',
    'beyond',
    'bill',
    'both',
    'bottom',
    'but',
    'by',
    'call',
    'can',
    'cannot',
    'cant',
    'co',
    'con',
    'could',
    'couldnt',
    'cry',
    'de',
    'describe',
    'detail',
    'do',
    'done',
    'down',
    'due',
    'during',
    'each',
    'eg',
    'eight',
    'either',
    'eleven',
    'else',
    'elsewhere',
    'empty',
    'enough',
    'etc',
    'even',
    'ever',
    'every',
    'everyone',
    'everything',
    'everywhere',
    'except',
    'few',
    'fifteen',
    'fifty',
    'fill',
    'find',
    'fire',
    'first',
    'five',
    'for',
    'former',
    'formerly',
    'forty',
    'found',
    'four',
    'from',
    'front',
    'full',
    'further',
    'get',
    'give',
    'go',
    'had',
    'has',
    'hasnt',
    'have',
    'he',
    'hence',
    'her',
    'here',
    'hereafter',
    'hereby',
    'herein',
    'hereupon',
    'hers',
    'herself',
    'him',
    'himself',
    'his',
    'how',
    'however',
    'hundred',
    'i',
    'ie',
    'if',
    'in',
    'inc',
    'indeed',
    'interest',
    'into',
    'is',
    'it',
    'its',
    'itself',
    'keep',
    'last',
    'latter',
    'latterly',
    'least',
    'less',
    'ltd',
    'made',
    'many',
    'may',
    'me',
    'meanwhile',
    'might',
    'mill',
    'mine',
    'more',
    'moreover',
    'most',
    'mostly',
    'move',
    'much',
    'must',
    'my',
    'myself',
    'name',
    'namely',
    'neither',
    'never',
    'nevertheless',
    'next',
    'nine',
    'no',
    'nobody',
    'none',
    'noone',
    'nor',
    'not',
    'nothing',
    'now',
    'nowhere',
    'of',
    'off',
    'often',
    'on',
    'once',
    'one',
    'only',
    'onto',
    'or',
    'other',
    'others',
    'otherwise',
    'our',
    'ours',
    'ourselves',
    'out',
    'over',
    'own',
    'part',
    'per',
    'perhaps',
    'please',
    'put',
    'rather',
    're',
    'same',
    'see',
    'seem',
    'seemed',
    'seeming',
    'seems',
    'serious',
    'several',
    'she',
    'should',
    'show',
    'side',
    'since',
    'sincere',
    'six',
    'sixty',
    'so',
    'some',
    'somehow',
    'someone',
    'something',
    'sometime',
    'sometimes',
    'somewhere',
    'still',
    'such',
    'system',
    'take',
    'ten',
    'than',
    'that',
    'the',
    'their',
    'them',
    'themselves',
    'then',
    'thence',
    'there',
    'thereafter',
    'thereby',
    'therefore',
    'therein',
    'thereupon',
    'these',
    'they',
    'thick',
    'thin',
    'third',
    'this',
    'those',
    'though',
    'three',
    'through',
    'throughout',
    'thru',
    'thus',
    'to',
    'together',
    'too',
    'top',
    'toward',
    'towards',
    'twelve',
    'twenty',
    'two',
    'un',
    'under',
    'until',
    'up',
    'upon',
    'us',
    'very',
    'via',
    'was',
    'we',
    'well',
    'were',
    'what',
    'whatever',
    'when',
    'whence',
    'whenever',
    'where',
    'whereafter',
    'whereas',
    'whereby',
    'wherein',
    'whereupon',
    'wherever',
    'whether',
    'which',
    'while',
    'whither',
    'who',
    'whoever',
    'whole',
    'whom',
    'whose',
    'why',
    'will',
    'with',
    'within',
    'without',
    'would',
    'yet',
    'you',
    'your',
    'yours',
    'yourself',
    'yourselves',
}
_WORD_RE = re.compile(r'[A-Za-z0-9]+')

def _tokenize(text: str) -> List[str]:
    if not isinstance(text, str):
        return []
    tokens = _WORD_RE.findall(text.lower())
    return [t for t in tokens if t and t not in ENGLISH_STOP_WORDS]

def _build_ngrams(tokens: List[str], min_n: int = 1, max_n: int = 2) -> List[str]:
    ngrams = []
    for n in range(min_n, max_n + 1):
        if len(tokens) < n:
            continue
        for i in range(len(tokens) - n + 1):
            ngrams.append(' '.join(tokens[i:i + n]))
    return ngrams

def _compute_tfidf_similarity_matrix_lite(
    docs: List[str],
    max_features: int = 500,
    min_df: Union[int, float] = 1,
    max_df: Union[int, float] = 0.8,
    ngram_range: Tuple[int, int] = (1, 2)
) -> np.ndarray:
    n_docs = len(docs)
    if n_docs == 0:
        return np.zeros((0, 0))

    doc_terms = []
    df_counts = Counter()
    tf_counts = Counter()

    for doc in docs:
        tokens = _tokenize(doc)
        terms = _build_ngrams(tokens, ngram_range[0], ngram_range[1])
        term_counts = Counter(terms)
        doc_terms.append(term_counts)
        for term in term_counts:
            df_counts[term] += 1
        tf_counts.update(term_counts)

    min_df_count = min_df * n_docs if isinstance(min_df, float) else min_df
    max_df_count = max_df * n_docs if isinstance(max_df, float) else max_df

    vocab = [
        term for term, df in df_counts.items()
        if df >= min_df_count and df <= max_df_count
    ]

    if not vocab:
        return np.zeros((n_docs, n_docs))

    vocab.sort(key=lambda t: (tf_counts[t], t), reverse=True)
    vocab = vocab[:max_features]

    vocab_index = {term: idx for idx, term in enumerate(vocab)}
    idf = {
        term: (math.log((1 + n_docs) / (1 + df_counts[term])) + 1.0)
        for term in vocab
    }

    vectors = np.zeros((n_docs, len(vocab)), dtype=float)
    for doc_idx, term_counts in enumerate(doc_terms):
        for term, count in term_counts.items():
            idx = vocab_index.get(term)
            if idx is None:
                continue
            vectors[doc_idx, idx] = count * idf[term]

    norms = np.linalg.norm(vectors, axis=1)
    norms[norms == 0] = 1.0
    vectors = vectors / norms[:, None]

    return vectors @ vectors.T


def calculate_skill_similarity(
    skills_df: pd.DataFrame,
    similarity_threshold: float = 0.75,
    installed_skills: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Calculate pairwise similarity scores between skills using TF-IDF.

    Args:
        skills_df: DataFrame with skills (must have 'name', 'description' columns)
        similarity_threshold: Minimum similarity score (0.0-1.0, default: 0.75)
        installed_skills: List of installed skill names for filtering matches

    Returns:
        DataFrame with similar skill pairs:
        - skill1_name: str
        - skill2_name: str
        - similarity_score: float
        - skill1_stars: int
        - skill2_stars: int
        - skill1_author: str
        - skill2_author: str

    Raises:
        ValueError: If skills_df is empty or missing required columns
        ImportError: If scikit-learn is not installed

    Example:
        >>> from parse_skill_manager import parse_skill_manager_response
        >>> skills_df = parse_skill_manager_response(skills)
        >>> similar = calculate_skill_similarity(skills_df, similarity_threshold=0.75)
        >>> print(f"Found {len(similar)} similar pairs")
    """
    logger.info(f"Starting similarity analysis (threshold={similarity_threshold})")

    # Validate input
    if skills_df.empty:
        raise ValueError("skills_df cannot be empty")

    required_columns = ['name', 'description']
    missing = set(required_columns) - set(skills_df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {missing}")

    # Filter out skills with empty descriptions
    valid_skills = skills_df[skills_df['description'].notna()].copy()
    valid_skills = valid_skills[valid_skills['description'].str.strip() != '']

    logger.info(f"Analyzing {len(valid_skills)} skills with valid descriptions")

    if len(valid_skills) < 2:
        logger.warning("Not enough skills with valid descriptions for similarity analysis")
        return pd.DataFrame()

    backend = os.environ.get("PDT_TFIDF_BACKEND", "sklearn").lower()
    logger.info(f"TF-IDF backend: {backend}")

    if backend == "lite":
        logger.debug("Using lightweight TF-IDF backend...")
        similarity_matrix = _compute_tfidf_similarity_matrix_lite(
            valid_skills['description'].tolist(),
            max_features=500,
            min_df=1,
            max_df=0.8,
            ngram_range=(1, 2)
        )
    else:
        # Import scikit-learn (lazy import)
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            raise ImportError(
                "scikit-learn is required for similarity analysis.\n"
                "Install with: pip install scikit-learn"
            )

        # Create TF-IDF vectors
        logger.debug("Creating TF-IDF vectors...")
        vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2),  # Include bigrams
            min_df=1,
            max_df=0.8
        )

        try:
            tfidf_matrix = vectorizer.fit_transform(valid_skills['description'])
        except Exception as e:
            logger.error(f"TF-IDF vectorization failed: {e}")
            return pd.DataFrame()

        # Calculate cosine similarity matrix (TF-IDF vectors are L2-normalized by default)
        logger.debug("Calculating cosine similarity matrix...")
        similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()

    if similarity_matrix.size == 0:
        logger.warning("Similarity matrix is empty")
        return pd.DataFrame()

    # Extract similar pairs above threshold
    logger.debug(f"Extracting pairs with similarity >= {similarity_threshold}")
    similar_pairs = []

    for i in range(len(valid_skills)):
        for j in range(i + 1, len(valid_skills)):
            similarity_score = similarity_matrix[i, j]

            if similarity_score >= similarity_threshold:
                skill1 = valid_skills.iloc[i]
                skill2 = valid_skills.iloc[j]

                # Filter by installed_skills if provided
                if installed_skills:
                    # At least one skill should be installed for replacement recommendations
                    if skill1['name'] not in installed_skills and skill2['name'] not in installed_skills:
                        continue

                similar_pairs.append({
                    'skill1_name': skill1['name'],
                    'skill2_name': skill2['name'],
                    'similarity_score': similarity_score,
                    'skill1_stars': skill1.get('stars', 0),
                    'skill2_stars': skill2.get('stars', 0),
                    'skill1_author': skill1.get('author', ''),
                    'skill2_author': skill2.get('author', ''),
                    'skill1_description': skill1.get('description', '')[:100] + '...',
                    'skill2_description': skill2.get('description', '')[:100] + '...'
                })

    logger.info(f"Found {len(similar_pairs)} similar pairs above threshold")

    if not similar_pairs:
        return pd.DataFrame()

    # Convert to DataFrame
    result_df = pd.DataFrame(similar_pairs)

    # Sort by similarity score descending
    result_df = result_df.sort_values('similarity_score', ascending=False).reset_index(drop=True)

    return result_df


def find_alternatives(
    installed_skill_name: str,
    all_skills_df: pd.DataFrame,
    similarity_threshold: float = 0.75,
    top_n: int = 5
) -> pd.DataFrame:
    """
    Find alternative skills functionally similar to an installed skill.

    Args:
        installed_skill_name: Name of the installed skill to find alternatives for
        all_skills_df: DataFrame with all available skills
        similarity_threshold: Minimum similarity score (default: 0.75)
        top_n: Maximum number of alternatives to return

    Returns:
        DataFrame with alternative skills:
        - name: str
        - similarity_score: float
        - stars: int
        - author: str
        - description: str

    Example:
        >>> alternatives = find_alternatives('code-reviewer', all_skills_df)
        >>> print(f"Found {len(alternatives)} alternatives")
    """
    logger.info(f"Finding alternatives for: {installed_skill_name}")

    # Find the installed skill in the DataFrame
    installed_skill = all_skills_df[all_skills_df['name'] == installed_skill_name]

    if installed_skill.empty:
        logger.warning(f"Skill '{installed_skill_name}' not found in database")
        return pd.DataFrame()

    # Calculate similarity with all other skills
    similarity_pairs = calculate_skill_similarity(
        all_skills_df,
        similarity_threshold=similarity_threshold
    )

    if similarity_pairs.empty:
        return pd.DataFrame()

    # Filter pairs where skill1 or skill2 is the installed skill
    alternatives = similarity_pairs[
        (similarity_pairs['skill1_name'] == installed_skill_name) |
        (similarity_pairs['skill2_name'] == installed_skill_name)
    ].copy()

    if alternatives.empty:
        logger.info(f"No alternatives found above threshold {similarity_threshold}")
        return pd.DataFrame()

    # Extract alternative skill info
    results = []
    for _, row in alternatives.iterrows():
        if row['skill1_name'] == installed_skill_name:
            alt_name = row['skill2_name']
            alt_stars = row['skill2_stars']
            alt_author = row['skill2_author']
            alt_desc = row['skill2_description']
        else:
            alt_name = row['skill1_name']
            alt_stars = row['skill1_stars']
            alt_author = row['skill1_author']
            alt_desc = row['skill1_description']

        results.append({
            'name': alt_name,
            'similarity_score': row['similarity_score'],
            'stars': alt_stars,
            'author': alt_author,
            'description': alt_desc
        })

    result_df = pd.DataFrame(results)

    # Sort by similarity score descending
    result_df = result_df.sort_values('similarity_score', ascending=False).reset_index(drop=True)

    # Return top N
    return result_df.head(top_n)


def aggregate_similarity_clusters(similarity_df: pd.DataFrame) -> List[List[str]]:
    """
    Group similar skills into clusters using connected components.

    Args:
        similarity_df: DataFrame from calculate_skill_similarity()

    Returns:
        List of clusters, where each cluster is a list of skill names

    Example:
        >>> similar = calculate_skill_similarity(skills_df)
        >>> clusters = aggregate_similarity_clusters(similar)
        >>> print(f"Found {len(clusters)} skill clusters")
    """
    if similarity_df.empty:
        return []

    # Build adjacency list for graph
    adjacency = {}

    for _, row in similarity_df.iterrows():
        skill1 = row['skill1_name']
        skill2 = row['skill2_name']

        if skill1 not in adjacency:
            adjacency[skill1] = set()
        if skill2 not in adjacency:
            adjacency[skill2] = set()

        adjacency[skill1].add(skill2)
        adjacency[skill2].add(skill1)

    # Find connected components (clusters)
    visited = set()
    clusters = []

    def dfs(node, cluster):
        """Depth-first search to find connected component."""
        visited.add(node)
        cluster.append(node)

        for neighbor in adjacency.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, cluster)

    for skill in adjacency:
        if skill not in visited:
            cluster = []
            dfs(skill, cluster)
            clusters.append(sorted(cluster))

    # Sort clusters by size descending
    clusters.sort(key=len, reverse=True)

    logger.info(f"Found {len(clusters)} similarity clusters")

    return clusters


def format_similarity_report(
    similarity_df: pd.DataFrame,
    top_n: int = 10
) -> str:
    """
    Format similarity analysis as human-readable report.

    Args:
        similarity_df: DataFrame from calculate_skill_similarity()
        top_n: Number of pairs to include in report

    Returns:
        Formatted string report

    Example:
        >>> similar = calculate_skill_similarity(skills_df)
        >>> report = format_similarity_report(similar)
        >>> print(report)
    """
    if similarity_df.empty:
        return "No similar skill pairs found"

    lines = [
        f"## 🔍 Skill Similarity Analysis\n",
        f"**Analysis Date:** {datetime.now().isoformat()}\n",
        "### Summary\n",
        f"- **Similar Pairs Found:** {len(similarity_df):,}\n",
        f"### Top {min(top_n, len(similarity_df))} Most Similar Pairs\n"
    ]

    # Add top N pairs
    top_pairs = similarity_df.head(top_n)

    for idx, pair in top_pairs.iterrows():
        lines.append(f"#### {idx + 1}. {pair['skill1_name']} ↔ {pair['skill2_name']}\n")
        lines.append(f"- **Similarity Score:** {pair['similarity_score']:.3f}")
        lines.append(f"- **{pair['skill1_name']}:** {pair['skill1_stars']} ⭐ by {pair['skill1_author']}")
        lines.append(f"- **{pair['skill2_name']}:** {pair['skill2_stars']} ⭐ by {pair['skill2_author']}")
        lines.append("")

    return "\n".join(lines)


# Main for testing
if __name__ == "__main__":
    # Enable logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s: %(message)s'
    )

    print("=" * 70)
    print("ANALYZE SIMILARITY - Test")
    print("=" * 70)

    # Test 1: Calculate similarity
    print("\n1. Testing calculate_skill_similarity():")
    try:
        from fetch_skill_manager import fetch_all_skills
        from parse_skill_manager import parse_skill_manager_response

        print("   Fetching skills from skill-manager...")
        skills, _ = fetch_all_skills(min_stars=100, max_months_old=6)
        df = parse_skill_manager_response(skills)

        # Limit to top 50 by stars for testing (avoid high computational cost)
        test_df = df.nlargest(50, 'stars')

        print(f"   Testing with {len(test_df)} popular skills...")
        similar = calculate_skill_similarity(
            test_df,
            similarity_threshold=0.75
        )

        print(f"   ✓ Found {len(similar)} similar pairs")

        if len(similar) > 0:
            print(f"\n   Top 3 most similar pairs:")
            for idx, pair in similar.head(3).iterrows():
                print(f"     {idx + 1}. {pair['skill1_name']} ↔ {pair['skill2_name']} (score: {pair['similarity_score']:.3f})")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Test 2: Find alternatives
    print("\n2. Testing find_alternatives():")
    if len(df) > 0:
        # Pick first skill as example
        example_skill = df.iloc[0]['name']
        print(f"   Finding alternatives for: {example_skill}")

        alternatives = find_alternatives(example_skill, df, similarity_threshold=0.70)
        print(f"   ✓ Found {len(alternatives)} alternatives")

        if len(alternatives) > 0:
            print(f"\n   Top 3 alternatives:")
            for idx, alt in alternatives.head(3).iterrows():
                print(f"     {idx + 1}. {alt['name']} (similarity: {alt['similarity_score']:.3f}, stars: {alt['stars']})")

    # Test 3: Aggregate clusters
    print("\n3. Testing aggregate_similarity_clusters():")
    if len(similar) > 0:
        clusters = aggregate_similarity_clusters(similar)
        print(f"   ✓ Found {len(clusters)} similarity clusters")

        if len(clusters) > 0:
            print(f"\n   Top 3 largest clusters:")
            for i, cluster in enumerate(clusters[:3], 1):
                print(f"     {i}. Cluster with {len(cluster)} skills: {', '.join(cluster[:5])}{'...' if len(cluster) > 5 else ''}")

    # Test 4: Format report
    print("\n4. Testing format_similarity_report():")
    report = format_similarity_report(similar, top_n=5)
    print("   ✓ Report generated:")
    print("\n" + "\n".join(["     " + line for line in report.split("\n")[:15]]))
    print("     ...")

    print("\n✅ All tests completed")
