package com.example.androidtestapp

import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.fragment.app.Fragment

class SimpleTextFragment : Fragment() {
    override fun onCreateView(
        inflater: android.view.LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?,
    ): View {
        val text = requireArguments().getString(ARG_TEXT).orEmpty()
        val textView = TextView(requireContext())
        textView.text = text
        textView.textSize = 20f
        textView.gravity = Gravity.CENTER
        textView.layoutParams = ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT,
        )
        return textView
    }

    companion object {
        private const val ARG_TEXT = "arg_text"

        fun newInstance(text: String): SimpleTextFragment {
            val fragment = SimpleTextFragment()
            fragment.arguments = Bundle().apply {
                putString(ARG_TEXT, text)
            }
            return fragment
        }
    }
}
