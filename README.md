# 🤖 AI-Powered Amazon Shopping Assistant for ChatGPT

**Shop smarter, not harder. Discover the perfect products on Amazon through natural conversations directly within ChatGPT.**

![AI-Powered Amazon Shopping Assistant Hero Image]



## 🌟 Overview

This project is an AI-powered Amazon Shopping Assistant built as a ChatGPT Master Control Program (MCP) server. It leverages the power of the Amazon Product Advertising API (PA API 5.0) to provide an intuitive and conversational shopping experience. Say goodbye to endless scrolling and confusing filters. Now, you can find, compare, and choose the best products simply by asking.

## ✨ Key Features

*   **🔍 Smart, Conversational Search:** Find products using natural language. Ask for what you want, just like you would talk to a person. For example, "Show me the best laptops for programming under ₹60,000 with at least 16GB of RAM."
*   **↔️ Side-by-Side Comparisons:** Easily compare product specifications, prices, and ratings in a clear and concise format.
*   **⭐ AI-Powered Review Summaries:** Get the gist of hundreds of customer reviews in seconds. Our AI analyzes and summarizes the key pros and cons.
*   **💰 Real-Time Pricing and Availability:** Access up-to-the-minute pricing information and stock availability to never miss a great deal.
*   **🎯 Personalized Recommendations:** The more you interact with the assistant, the better it understands your preferences, offering tailored suggestions.
*   **⚡ Prime and Delivery Information:** Filter for Prime-eligible items and get delivery information to make informed purchasing decisions.

## 🚀 The Problem We Solve

Shopping on Amazon can be overwhelming. With millions of products, it's challenging to find the right one. You might spend hours sifting through search results, comparing prices, and trying to decipher fake reviews.

Our ChatGPT Shopping Assistant cuts through the noise. It acts as your personal shopper, understanding your needs and providing curated, data-driven recommendations in an instant. This saves you time, reduces decision fatigue, and helps you make confident purchasing decisions.

## 🛠️ Tech Stack

This project is built with a modern and robust technology stack to ensure a seamless and efficient user experience:

*   **Backend:** Python with FastAPI for building a high-performance API.
*   **AI Integration:** OpenAI's MCP protocol for seamless integration with ChatGPT.
*   **Data Source:** Amazon Product Advertising API 5.0 for comprehensive and real-time product data.
*   **Frontend (Landing Page):** Next.js with Tailwind CSS for a fast, responsive, and beautifully designed user interface.
*   **UI Components:** Shadcn for accessible and reusable UI components.
*   **Animations:** Framer Motion for smooth and engaging animations.
*   **Deployment:** The landing page is deployed as a static site on GitHub Pages.

## 🏁 Getting Started

### Prerequisites

*   An OpenAI account with access to ChatGPT.
*   An Amazon Associates account to obtain API keys for the Product Advertising API.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/[YOUR_GITHUB_USERNAME]/[YOUR_REPOSITORY_NAME].git
    cd [YOUR_REPOSITORY_NAME]
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure your environment variables:**

    Create a `.env` file in the root directory and add your API keys:
    ```
    AMAZON_ACCESS_KEY=your_amazon_access_key
    AMAZON_SECRET_KEY=your_amazon_secret_key
    AMAZON_ASSOCIATE_TAG=your_amazon_associate_tag
    ```

4.  **Run the server:**
    ```bash
    uvicorn main:app --reload
    ```

## 🎥 Demo

Check out this short video to see the AI Shopping Assistant in action:

[Link to your demo video on YouTube or Loom]

## 🤝 How to Contribute

We welcome contributions from the community! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some amazing feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a pull request.

Please read our `CONTRIBUTING.md` for more details on our code of conduct and the process for submitting pull requests.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

## ⚖️ Affiliate Disclosure

This project is a participant in the Amazon Services LLC Associates Program, an affiliate advertising program designed to provide a means for sites to earn advertising fees by advertising and linking to Amazon. We earn a small commission from qualifying purchases made through our links at no additional cost to you.

---